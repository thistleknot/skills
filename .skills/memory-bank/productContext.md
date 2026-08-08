# Product Context

## Why This Exists
Personal quant pipeline running in a Roth IRA via IBKR. Separate from day job.
Goal is systematic, rules-based portfolio management with minimal manual intervention.
Homelab AI stack supports both the quant work and general LLM experimentation.

## How It Should Work
- Pipeline runs on 13-week rolling tranches
- XGBoost business cycle classifier on FRED indicators drives regime detection
- Markowitz optimization with MAD-based Sharpe, fed by median-mean GAM normalized expected returns
- Parkinson volatility for bracket orders
- IBKR execution layer is the terminal output
- Two-stage optimizer consistently favors GLDM/XES/COPX cluster
- Current thesis: dollar debasement + geopolitical risk (Operation Epic Fury, US-Iran)
- Portfolio ratio: ~1.3:1 GLDM:XES reflecting near-term XES catalyst asymmetry

## User Experience Goals
- Run pipeline, get orders, approve, done
- Minimal friction between signal and execution
- Audit trail via sqlite so any run is reproducible
