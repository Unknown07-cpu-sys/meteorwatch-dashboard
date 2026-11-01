# Phase 1 review notes

## Scope

Phase 1 adds defensive report loading, shared catalogue summaries, consistent CSV/XLSX exports, provider-contract checks, Streamlit page tests, chart layout tests, browser checks and CI.

## Issues addressed

1. Missing-energy records remain visible when a minimum-energy filter is applied because the threshold cannot be evaluated for an unknown value.
2. Custom OpenAI-compatible endpoints are restricted to supported HTTPS provider hosts. Credentials, custom ports, query strings and fragments are rejected, malformed ports return a clear validation error, and redirects are not followed.
3. Cartesian Plotly charts reserve room for axis labels. Timeline, outcome and data-completeness plots have larger margins; geo charts retain their edge-to-edge layout.
4. CSV/XLSX export tests inspect serialized output with blank cells preserved, rather than converting pandas missing values to the string `nan`.
5. The report loader normalises date, numeric, boolean and coordinate fields while keeping missing and unrecognised values unknown.
6. The devcontainer no longer disables Streamlit's XSRF protection.
7. GitHub Actions requests read-only repository contents permission and applies job time limits.

## Validation

The reviewed Phase 1 archive completed Python compilation and its unit suite: **182 tests discovered, 174 passed and 8 skipped**. The skipped tests require the real Streamlit and Plotly page-testing environment. Browser layout checks and live provider checks were not run as part of that local review.

CI is configured to run the unit suite and browser layout tests. Review the GitHub Actions run and its screenshot artifact before treating the browser layout as verified.

## Scientific limits

This project analyses historical reported fireball observations. It is not a future-impact predictor or operational warning system. Detector flags are prompts for human review, not verified physical anomalies or hazard labels. Missing measurements remain missing, and reported peak-brightness coordinates are not confirmed ground-impact locations.
