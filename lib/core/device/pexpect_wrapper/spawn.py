from pexpect import spawn as PexpectSpawn


class Spawn(PexpectSpawn):

    def __init__(
        self, command, buffer_type, encoding="utf-8", codec_errors="ignore", **kwargs
    ):
        super().__init__(
            command, encoding=encoding, codec_errors=codec_errors, **kwargs
        )
        self.buffer_type = buffer_type
        self._buffer = self.buffer_type()
        # The buffer may be trimmed for efficiency reasons.  This is the
        # untrimmed buffer, used to create the before attribute.
        self._before = self.buffer_type()
