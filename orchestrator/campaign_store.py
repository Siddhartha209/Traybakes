from __future__ import annotations

import json
import re
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campaigns.db"

RECENCY_HALF_LIFE_DAYS = 30.0
RECENCY_WEIGHT_FLOOR = 0.3
DEDUP_SIMILARITY_THRESHOLD = 0.55

_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "for", "with", "your",
    "our", "is", "are", "it", "its", "on", "at", "you", "that", "this",
    "be", "as", "from", "we", "us", "today", "try", "them",
}


@dataclass
class CampaignRecord:
    id: int | None
    timestamp: float
    goal: str
    content_type: str
    tone: str
    captions: list[str] = field(default_factory=list)
    selected_caption: str | None = None
    rating: int | None = None


def get_connection(db_path: str | Path = DEFAULT_DB_PATH):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    _init_schema(conn)
    return conn


def _init_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            goal TEXT NOT NULL,
            content_type TEXT,
            tone TEXT,
            captions_json TEXT NOT NULL,
            selected_caption TEXT,
            rating INTEGER
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS caption_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            caption_id TEXT NOT NULL,
            caption TEXT NOT NULL,
            rating INTEGER NOT NULL,
            created_at REAL NOT NULL,
            FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_caption_feedback_rating
        ON caption_feedback(rating)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_campaign_rating
        ON campaigns(rating)
        """
    )

    try:
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_caption_feedback_unique
            ON caption_feedback(campaign_id, caption_id)
            """
        )
    except sqlite3.IntegrityError:
        print(
            "[campaign_store] WARNING: could not create unique index on "
            "caption_feedback(campaign_id, caption_id) — duplicate rows "
            "already exist. Re-rating a caption will insert extra rows "
            "until these are cleaned up manually."
        )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS caption_edits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            caption_id TEXT NOT NULL,
            original_caption TEXT NOT NULL,
            edited_caption TEXT NOT NULL,
            removed_phrases_json TEXT NOT NULL,
            added_phrases_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_caption_edits_created_at
        ON caption_edits(created_at)
        """
    )

    conn.commit()


def save_campaign(conn, goal, content_type, tone, captions):
    cur = conn.execute(
        """
        INSERT INTO campaigns (timestamp, goal, content_type, tone, captions_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (time.time(), goal, content_type, tone, json.dumps(captions)),
    )
    conn.commit()
    return cur.lastrowid


def save_campaign_from_state(conn, state):
    captions = getattr(state, "captions", []) or []
    caption_texts = [
        c.get("caption", "") if isinstance(c, dict) else str(c) for c in captions
    ]

    content_type = getattr(state, "content_type", "") or ""
    tone = getattr(state, "tone", "") or ""

    return save_campaign(
        conn,
        state.goal,
        content_type,
        tone,
        caption_texts,
    )


def record_selection(conn, campaign_id, selected_caption):
    conn.execute(
        """
        UPDATE campaigns
        SET selected_caption=?
        WHERE id=?
        """,
        (selected_caption, campaign_id),
    )
    conn.commit()


def record_rating(conn, campaign_id, caption_id, caption, rating):
    if rating not in (1, -1):
        raise ValueError("rating must be 1 or -1")

    conn.execute(
        """
        UPDATE campaigns
        SET rating=?
        WHERE id=?
        """,
        (rating, campaign_id),
    )
    conn.commit()


def record_caption_rating(conn, campaign_id, caption_id, caption, rating):
    if rating not in (1, -1):
        raise ValueError("rating must be 1 or -1")

    try:
        conn.execute(
            """
            INSERT INTO caption_feedback (campaign_id, caption_id, caption, rating, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(campaign_id, caption_id)
            DO UPDATE SET
                rating=excluded.rating,
                caption=excluded.caption,
                created_at=excluded.created_at
            """,
            (campaign_id, caption_id, caption, rating, time.time()),
        )
    except sqlite3.OperationalError:
        conn.execute(
            """
            INSERT INTO caption_feedback (campaign_id, caption_id, caption, rating, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (campaign_id, caption_id, caption, rating, time.time()),
        )

    conn.commit()


def _extract_phrase_diff(original: str, edited: str) -> tuple[list[str], list[str]]:
    """
    Word-level diff between an original caption and its manually edited
    version. Returns (removed_phrases, added_phrases) — the specific spans
    of text that changed, rather than treating the whole caption as one
    like/dislike signal.
    """
    orig_words = original.split()
    edit_words = edited.split()
    matcher = SequenceMatcher(a=orig_words, b=edit_words)

    removed, added = [], []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("delete", "replace"):
            phrase = " ".join(orig_words[i1:i2]).strip()
            if phrase:
                removed.append(phrase)
        if tag in ("insert", "replace"):
            phrase = " ".join(edit_words[j1:j2]).strip()
            if phrase:
                added.append(phrase)

    return removed, added


def record_caption_edit(conn, campaign_id, caption_id, original_caption, edited_caption):
    """
    Records a manual caption edit as a targeted correction signal, storing
    exactly which phrases were removed/added rather than a whole-caption
    like/dislike. A no-op if the save didn't actually change the text.
    """
    if original_caption.strip() == edited_caption.strip():
        return

    removed, added = _extract_phrase_diff(original_caption, edited_caption)
    if not removed and not added:
        return

    conn.execute(
        """
        INSERT INTO caption_edits
            (campaign_id, caption_id, original_caption, edited_caption,
             removed_phrases_json, added_phrases_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            campaign_id,
            caption_id,
            original_caption,
            edited_caption,
            json.dumps(removed),
            json.dumps(added),
            time.time(),
        ),
    )
    conn.commit()


def get_learned_edit_phrases(conn, top_k=10, min_occurrences=1) -> list[str]:
    """
    Returns the most frequently/recently removed phrases across past manual
    edits — a dynamic, learned equivalent of BANNED_PHRASES. Single-word
    removals are excluded since those are usually typo fixes rather than
    style feedback.
    """
    rows = conn.execute(
        "SELECT removed_phrases_json, created_at FROM caption_edits ORDER BY created_at DESC"
    ).fetchall()

    counts = Counter()
    latest_seen = {}

    for row in rows:
        phrases = json.loads(row["removed_phrases_json"])
        for phrase in phrases:
            if len(phrase.split()) < 2:
                continue
            key = phrase.lower()
            counts[key] += 1
            latest_seen.setdefault(key, row["created_at"])

    ranked = sorted(
        (p for p, c in counts.items() if c >= min_occurrences),
        key=lambda p: (counts[p], latest_seen[p]),
        reverse=True,
    )
    return ranked[:top_k]


def _normalized_words(text):
    words = re.findall(r"[a-zA-Z']+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _word_overlap_ratio(text_a, text_b):
    # Calculates standard Jaccard distance over normalized word sets to evaluate text similarity.
    words_a = _normalized_words(text_a)
    words_b = _normalized_words(text_b)

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)


def _recency_weight(created_at, now):
    # Exponential decay function based on age days to prevent older liked examples from dominating search results.
    age_days = max((now - created_at) / 86400.0, 0.0)
    weight = 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)
    return max(weight, RECENCY_WEIGHT_FLOOR)


def get_similar_liked_captions(
    conn,
    new_goal,
    top_k=3,
    min_similarity=0.1,
    content_type=None,
):
    if not _SKLEARN_AVAILABLE:
        return []

    query = """
        SELECT
            c.id AS campaign_id,
            c.goal,
            c.content_type,
            f.caption,
            f.created_at
        FROM caption_feedback f
        JOIN campaigns c ON c.id=f.campaign_id
        WHERE f.rating=1
    """
    params = ()

    if content_type:
        query += " AND c.content_type=?"
        params = (content_type,)

    liked_rows = conn.execute(query, params).fetchall()
    if not liked_rows:
        return []

    disliked_rows = conn.execute(
        """
        SELECT caption
        FROM caption_feedback
        WHERE rating=-1
        """
    ).fetchall()
    disliked_texts = [r["caption"] for r in disliked_rows]

    goals = [r["goal"] for r in liked_rows]
    corpus = goals + [new_goal]

    vectorizer = TfidfVectorizer(stop_words="english")

    try:
        matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        return []

    similarities = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
    now = time.time()

    scored = []
    for score, row in zip(similarities, liked_rows):
        if score < min_similarity:
            continue

        weight = _recency_weight(row["created_at"], now)
        combined = score * weight
        scored.append((combined, score, row))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for combined, raw_score, row in scored:
        caption = row["caption"]

        # Filters out captions matching disliked phrasing to prevent reinforcing negative traits.
        if any(
            _word_overlap_ratio(caption, disliked) >= DEDUP_SIMILARITY_THRESHOLD
            for disliked in disliked_texts
        ):
            continue

        # Suppresses near-duplicate outputs within the top-k result list.
        if any(
            _word_overlap_ratio(caption, chosen) >= DEDUP_SIMILARITY_THRESHOLD
            for chosen in results
        ):
            continue

        results.append(caption)

        if len(results) >= top_k:
            break

    return results


def get_campaign(conn, campaign_id):
    row = conn.execute(
        """
        SELECT *
        FROM campaigns
        WHERE id=?
        """,
        (campaign_id,),
    ).fetchone()

    if row is None:
        return None

    return CampaignRecord(
        id=row["id"],
        timestamp=row["timestamp"],
        goal=row["goal"],
        content_type=row["content_type"],
        tone=row["tone"],
        captions=json.loads(row["captions_json"]),
        selected_caption=row["selected_caption"],
        rating=row["rating"],
    )


def get_feedback_stats(conn):
    total = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]

    liked = conn.execute(
        """
        SELECT COUNT(*)
        FROM caption_feedback
        WHERE rating=1
        """
    ).fetchone()[0]

    disliked = conn.execute(
        """
        SELECT COUNT(*)
        FROM caption_feedback
        WHERE rating=-1
        """
    ).fetchone()[0]

    return {
        "total_campaigns": total,
        "liked_captions": liked,
        "disliked_captions": disliked,
        "total_feedback": liked + disliked,
    }