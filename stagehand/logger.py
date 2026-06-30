import logging
import threading
from collections import deque

class Logger(logging.Logger):
    def makeRecord(self, name, *args, **kwargs):
        if name.startswith('stagehand.'):
            name = name[10:]
        return super().makeRecord(name, *args, **kwargs)

    def debug2(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.DEBUG2):
            self._log(logging.DEBUG2, msg, args, **kwargs)

logging.DEBUG2 = 5
logging.addLevelName(logging.DEBUG2, 'DEBUG2')
logging.setLoggerClass(Logger)
logging.basicConfig(format='%(asctime)s [%(levelname)s] %(name)s: %(message)s', level=logging.WARN)


class MemoryLogHandler(logging.Handler):
    """Keeps the last `capacity` log records in memory for web UI access."""
    def __init__(self, capacity=1000):
        super().__init__()
        self._records = deque(maxlen=capacity)
        self._seq = 0
        self._lock = threading.Lock()
        self.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))

    def emit(self, record):
        try:
            msg = self.format(record)
        except Exception:
            msg = str(record.getMessage())
        with self._lock:
            self._seq += 1
            self._records.append({
                'seq': self._seq,
                'level': record.levelname,
                'msg': msg,
            })

    def get_records(self, since=0):
        with self._lock:
            return [r for r in self._records if r['seq'] > since]

    @property
    def seq(self):
        with self._lock:
            return self._seq


memory_handler = MemoryLogHandler()
logging.getLogger().addHandler(memory_handler)
