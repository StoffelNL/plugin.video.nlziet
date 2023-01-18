import logging, xbmc
from resources.lib.base.l1.constants import ADDON_ID

class Logger(logging.Logger):
    def __call__(self, *args, **kwargs):
        self.debug(*args, **kwargs)

class LoggerHandler(logging.StreamHandler):
    LEVELS = {
        logging.NOTSET   : xbmc.LOGNONE,
        logging.DEBUG    : xbmc.LOGDEBUG,
        logging.INFO     : xbmc.LOGINFO,
        logging.ERROR    : xbmc.LOGERROR,
        logging.CRITICAL : xbmc.LOGFATAL,
    }

    def emit(self, record):
        msg = self.format(record)
        level = self.LEVELS.get(record.levelno, xbmc.LOGDEBUG)
        xbmc.log(str(msg), level)

logging.setLoggerClass(Logger)

formatter = logging.Formatter(u'%(name)s - %(message)s')

handler = LoggerHandler()
handler.setFormatter(formatter)

log = logging.getLogger(ADDON_ID)
log.addHandler(handler)
log.setLevel(logging.DEBUG)