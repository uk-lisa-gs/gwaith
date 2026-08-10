"""Signal subtraction for GWAITH timeseries data."""

from __future__ import annotations

import copy
import logging

from gwaith.types import TimeSeries

logger = logging.getLogger("gwaith.subtraction.subtraction")


def subtract_signals(
    data: dict[TimeSeries], signals: list[dict[TimeSeries]], channels: list
) -> dict[TimeSeries]:
    """Subtract each signal from *data_ts* on a channel-by-channel basis.

    Raises
    ------
    ValueError
        If any of the given channels are not in data or any signal dict
        If any signal's length, ``epoch``, or ``delta_t`` differs from
        *data_ts*.

    """
    residual = copy.deepcopy(data)
    for channel in channels:
        logger.info("Subtracting in channel %s", channel)
        if channel not in data_ts:
            raise ValueError(f"Channel {channel} not in data timeseries")
        data_ts = data[channel]
        for i, signal in enumerate(signals):
            logger.info("Subtracting signal %d", i)
            if channel not in signal:
                raise ValueError(f"Channel {channel} not in signal {i} timeseries")
            signal_ts = signal[channel]
            if len(signal_ts.data) != len(data_ts.data):
                raise ValueError(
                    f"Signal {i} length {len(signal.data)} != data length "
                    f"{len(data_ts.data)}"
                )
            if signal_ts.epoch != data_ts.epoch:
                raise ValueError(
                    f"Signal {i} epoch {signal.epoch} != data epoch {data_ts.epoch}"
                )
            if signal_ts.delta_t != data_ts.delta_t:
                raise ValueError(
                    f"Signal {i} delta_t {signal.delta_t} != data delta_t "
                    f"{data_ts.delta_t}"
                )

            residual[channel] -= data_ts

    return residual
