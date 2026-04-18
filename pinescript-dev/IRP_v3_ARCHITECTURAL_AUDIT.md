# ARCHITECTURAL AUDIT & REBUILD SPECIFICATION
## SYSTEM: Institutional Range Predictor (IRP v3)
## TARGET AUDIENCE: Next-Generation AI Engineering Agent

> [!CAUTION]
> **CRITICAL WARNING TO NEXT AGENT:** 
> Do not attempt to patch or visually tweak the current `f_yz`, `f_har`, or `f_daily` logic. The system is suffering from profound mathematical structural flaws at the base input level. Your task is a surgical architectural rewrite of the variance generation pipeline. Follow this specification exactly. Any deviation will result in mathematical hallucination and trading losses.

---

### 1. EXECUTIVE SUMMARY

The current model (IRP v3) is visually deterministic and aesthetically premium, but it is **mathematically compromised** for its intended use case: high-precision intraday scalping. 

The indicator fails to react to tight consolidations and remains blind to live structural breakouts. This is not a visual bug; it is a structural mathematical failure. The underlying variance calculations suffer from catastrophic "double-smoothing," which destroys the Heterogeneous Autoregressive (HAR-RV) multi-frequency matrix. Furthermore, the model's rigid daily anchoring creates a fundamental blindspot during live intraday volatility expansions. 

The engine requires a complete mathematical rewrite of its base inputs to become a hyper-reactive scalping tool.

---

### 2. FATAL ARCHITECTURAL FLAWS (THE ROOT CAUSES)

#### FLAW A: The Double-Smoothing Collinearity Trap (FATAL)
*   **The Intent:** The HAR-RV model requires a fast 1-day variance component ($RV_d$), a 5-day component ($RV_w$), and a 22-day component ($RV_m$) to capture the heterogeneous memory of market agents (scalpers, swing traders, and institutions).
*   **The Implementation Error:** The current code feeds `f_yz(i_yz)` (where `i_yz` = 10) directly into the $RV_d$ base. `f_yz` calculates the Yang-Zhang variance *over the preceding 10 days*. 
*   **The Consequence:** The fastest reaction component in the model now has a 10-day memory. Consequently, $RV_w$ becomes a 15-day memory, and $RV_m$ becomes a 32-day memory. Because these three inputs are highly collinear (they are all smoothed versions of the same 10-day curve), the Ridge OLS regression correctly identifies the redundancy and dumps 100% of the weight onto $\beta_d$ (seen in the table as `1.14`), driving $\beta_w$ and $\beta_m$ to 0. 
*   **The Result:** The advanced HAR-RV model has effectively collapsed into a single, slow 10-day moving average. It cannot shrink during 2-day consolidations and cannot expand during immediate breakouts.

#### FLAW B: Macro Anchoring vs. Micro Intraday Execution (FATAL FOR SCALPING)
*   **The Intent:** The indicator anchors its bands to the previous confirmed daily close (`close[1]` in D context).
*   **The Implementation Error:** While mathematically sound for end-of-day options pricing, this fixed anchor makes the bands fully static and oblivious during the intraday session. 
*   **The Consequence:** If a massive structural breakout occurs at 10:15 AM, the model's anchor does not trail, and the band width (determined by yesterday's HAR prediction) does not expand. The scalper is left with broken, utterly irrelevant bounds until the next day's open. The model operates exclusively on *macro-historical inertia* rather than *real-time micro-structural flow*.

#### FLAW C: Bipower Variation (BPV) Information Loss (MODERATE)
*   **The Intent:** BPV is used to filter out jumps from the continuous variance.
*   **The Implementation Error:** It relies strictly on daily close-to-close returns.
*   **The Consequence:** Massive intraday volatility spikes that revert before the daily close are completely invisible to the BPV calculation. It only detects overnight gaps or heavy trend days, ignoring intraday structural breaks.

---

### 3. EXPLICIT REBUILD INSTRUCTIONS FOR THE NEXT AI AGENT

To correct these flaws and transition the tool from a "slow options pricing envelope" to a "hyper-reactive institutional scalping model," you **MUST** execute the following exact architectural changes:

#### Step 1: Decouple Fast Variance from Slow Variance
*   The $RV_d$ component for the HAR model **MUST be a true, highly reactive variance**. 
*   **Action:** Instead of feeding a 10-day YZ average into $RV_d$, calculate a pure 1-day or 2-day realized variance (or a 1-period YZ estimator). This will immediately revive the HAR model, distribute the beta weights correctly across d/w/m, and allow the bands to instantly choke tight during a brief consolidation.

#### Step 2: Real-Time Intraday Anchor Trailing
*   Replace the static previous-day close anchor with a dynamic intraday anchor appropriate for scalping.
*   **Action:** Use a dynamic center-of-gravity, such as the **Session Open**, the **Daily VWAP**, or a **rolling fast EMA**. The bands must project *from the current battleground*, not yesterday's graveyard.

#### Step 3: Dynamic Intraday Volatility Injection
*   The band width must incorporate live, real-time intraday variance. 
*   **Action:** Do NOT use the pure daily HAR prediction for live intraday bounds. Instead, use the daily HAR prediction as a *macro baseline*, and dynamically scale it using a real-time intraday continuous true range or an intrabar variance estimator. If price suddenly goes parabolic at 12:00 PM, the bands must immediately expand to capture the new flow regime.

#### Step 4: Preserve Visual Determinism and Pine v6 Compliance
*   **Action:** You must maintain the exact current color generation logic (using explicit variables like `c_hi_bot`, `c_hi_top` instead of inline `color.rgb()` calls) to bypass known Pine v6 linter parsing bugs.
*   **Action:** Maintain the `table.new()` named arguments (`position=`, `columns=`, etc.).
*   **Action:** Keep the phantom plot logic (`linewidth=1` + `display=display.none`) to preserve the glassmorphic gradient fills without violating compiler rules.

> [!IMPORTANT]
> **Final Directive to Next Agent:**
> Do not debate the math. The collinearity of the current implementation is mathematically proven. Rip out the 10-day smoothing from the HAR base input, modernize the anchor for intraday action, and inject real-time volatility expansion. Make it sharp. Make it lethal.
