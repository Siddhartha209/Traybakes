from PySide6.QtCore import QObject, Signal, Slot

from img_gen.generator import apply_tweak


class ImageTweakWorker(QObject):
    """
    Runs Gemini image editing in the background
    so the PySide UI does not freeze.
    """

    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        state,
        tweak_prompt: str
    ):
        super().__init__()

        self.state = state
        self.tweak_prompt = tweak_prompt


    @Slot()
    def run(self):

        try:

            updated_state = apply_tweak(
                self.state,
                self.tweak_prompt
            )

            errors = getattr(
                updated_state,
                "errors",
                []
            )

            if errors:

                error = errors[-1]

                self.error.emit(
                    error.get(
                        "error",
                        "Unknown error"
                    )
                )

                return

            images = getattr(
                updated_state,
                "images",
                {}
            )

            output_path = None

            if isinstance(images, dict):
                output_path = images.get(
                    "generated_output_path"
                )


            if not output_path:

                self.error.emit(
                    "Gemini returned no edited image"
                )

                return

            self.finished.emit(
                updated_state
            )


        except Exception as e:

            self.error.emit(
                str(e)
            )