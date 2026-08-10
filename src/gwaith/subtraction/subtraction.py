"""Signal subtraction for GWAITH timeseries data."""

from __future__ import annotations

import logging

from gwaith.types import TimeSeries

logger = logging.getLogger("gwaith.subtraction.subtraction")


def subtract_signals(
    data_dict: dict[TimeSeries], signals: list[dict[TimeSeries]], channels: list
) -> dict[TimeSeries]:
    """Subtract each signal from *data_ts* on a channel-by-channel basis.

    Raises
    ------
    ValueError
        If any of the given channels are not in data or any signal dict
        If any signal's length, ``epoch``, or ``delta_t`` differs from
        *data_ts*.

    """
    residual = data_dict.copy()
    for channel in channels:
        logger.info("Subtracting in channel %s", channel)
        if channel not in residual:
            raise ValueError(f"Channel {channel} not in data timeseries")

        for i, signal in enumerate(signals):
            logger.info("Subtracting signal %d", i)
            if channel not in signal:
                raise ValueError(f"Channel {channel} not in signal {i} timeseries")

            residual[channel] -= signal[channel]

    return residual
