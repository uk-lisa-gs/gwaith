"""Signal subtraction for GWAITH timeseries data."""

from __future__ import annotations

from gwaith.types import TimeSeries


def subtract_signals(data_ts: TimeSeries, signals: list[TimeSeries]) -> TimeSeries:
    """Subtract each signal from *data_ts*, returning a new :class:`TimeSeries`.

    Raises
    ------
    ValueError
        If any signal's length, ``epoch``, or ``delta_t`` differs from *data_ts*.
    """
    for i, sig in enumerate(signals):
        if len(sig.data) != len(data_ts.data):
            raise ValueError(
                f"Signal {i} length {len(sig.data)} != data length {len(data_ts.data)}"
            )
        if sig.epoch != data_ts.epoch:
            raise ValueError(
                f"Signal {i} epoch {sig.epoch} != data epoch {data_ts.epoch}"
            )
        if sig.delta_t != data_ts.delta_t:
            raise ValueError(
                f"Signal {i} delta_t {sig.delta_t} != data delta_t {data_ts.delta_t}"
            )

    residual = data_ts
    for sig in signals:
        residual = residual - sig

    return residual
