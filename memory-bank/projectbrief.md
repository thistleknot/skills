# Project Brief

## Purpose
This memory bank covers Jos Hua's personal technical work outside of Boeing:
quantitative finance pipeline, homelab AI infrastructure, and associated tooling.
Not Boeing work. Not subject to Boeing IP constraints.

## Core Requirements
- Quant pipeline must be reproducible and checkpoint-based (sqlite load-if-exists)
- All price data via stooq through pandas_datareader. Never yfinance.
- Fundamentals via FMP free tier or SEC EDGAR XBRL API
- Local AI inference preferred over cloud where latency allows
- Code must be complete â€” no snippets, no placeholders

## Out of Scope
- Boeing proprietary systems
- Yahoo Finance or yfinance in any form
- Cloud-first solutions where local inference is viable
