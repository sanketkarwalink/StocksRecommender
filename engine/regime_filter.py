from data.prices import TrendInputs, TrendState, determine_trend_state


def market_regime_is_cautious(nifty_inputs: TrendInputs, cfg: dict) -> bool:
    state = determine_trend_state(nifty_inputs, cfg)
    return state == TrendState.PAUSE or nifty_inputs.price < nifty_inputs.sma200
