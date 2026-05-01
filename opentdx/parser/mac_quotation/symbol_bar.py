from datetime import datetime
import struct
from typing import override

from opentdx.const import EX_MARKET, MARKET, PERIOD, ADJUST
from opentdx.parser.baseParser import BaseParser, register_parser
from opentdx.utils.help import combine_to_datetime


@register_parser(0x122E, 1)
class SymbolBar(BaseParser):
    def __init__(self, market: MARKET | EX_MARKET, code: str, period: PERIOD, times: int = 1, start: int = 0, count: int = 700, fq: ADJUST = ADJUST.NONE):
        self.body = struct.pack("<H22sHH I HH bbb bH4s", market.value, code.encode("gbk"), period.value, times, start, count, fq.value, 1, 1, 0, 1, 0, b"")
        self.is_ex = isinstance(market, EX_MARKET)

    @override
    def deserialize(self, data):
        market, symbol, period, unknown, count, start = struct.unpack_from("<H12s10xBHHI", data)
        
        charts = []
        for i in range(count):
            ymd, time_num, open, high, low, close, amount, vol, float_shares = struct.unpack_from("<II7f", data, 33 + i * 36)

            # 如果是美股或者期货, time_num是中国时间, 但ymd是美国日期. 例如 2026-03-26 22:30:00 的k线, TDX数据返回的是 2026-03-25 22:30:00 
            charts.append({
                "datetime": combine_to_datetime(ymd, time_num, period < 4 or period == 7 or period == 8),
                "open": open,
                "high": high,
                "low": low,
                "close": close,
                "vol": vol,
                "amount": amount,
                "float_shares": float_shares,  # 流通股
            })

        name, decimal, category, vol_unit, date_raw, time_raw, pre_close, open, high, low, close, momentum, vol, amount, turnover, avg, industry = struct.unpack_from("<44sBHf5x2I5ffIf12x2fI", data, 33 + count * 36)

        return {
            "market": MARKET(market) if not self.is_ex else EX_MARKET(market),
            "code": symbol.decode("gbk").rstrip('\x00'),
            "name": name.decode("gbk").rstrip('\x00'),
            "decimal": decimal,
            "category": category,
            "vol_unit": vol_unit,
            "time": datetime(date_raw // 10000, (date_raw % 10000) // 100, date_raw % 100, time_raw // 10000, (time_raw % 10000) // 100, time_raw % 100),
            "pre_close": pre_close,
            "open": open,
            "high": high,
            "low": low,
            "close": close,
            "momentum": momentum,
            "vol": vol,
            "amount": amount,
            "turnover": turnover,
            "avg": avg,
            "industry": industry,
            "period": PERIOD(period),
            "count": count,
            "start": start,
            "charts": charts
        }
