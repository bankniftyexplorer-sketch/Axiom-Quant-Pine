import os
import re

in_file = "/home/km/PineWorkspace/pinescript-dev/IRP v5 — Dynamic Range Cone Engine.txt"
out_file = "/home/km/PineWorkspace/pinescript-dev/IRP v7 — Adaptive Conformal Range Cone Quant Engine.txt"

with open(in_file, "r") as f:
    code = f.read()

# 1. Update Header
code = code.replace("IRP v5 — Dynamic Range Cone Engine", "IRP v7 — Adaptive Conformal Range Cone Quant Engine")
code = code.replace("indicator('IRP v5 [Predicted Range · CONE]'", "indicator('IRP v7 [Adaptive Conformal Range · CONE]'")

# 2. Update Inputs
old_inputs = """i_sigma  = input.float(1.0, 'Sigma Level', minval=0.5, maxval=3.0, step=0.25, group='Range', tooltip='1.0=Expected Move (68%), 1.5=Probable Range (87%), 2.0=Conservative (95%)')
i_sigma2 = input.float(0.0, 'Secondary Sigma (0=off)', minval=0.0, maxval=3.0, step=0.25, group='Range', tooltip='Optional second band. Set 0 to disable.')"""
new_inputs = """i_adapt_cal = input.bool(true, 'Adaptive Conformal Calibration', group='Calibration')
i_cal_len   = input.int(60, 'Calibration Sessions', minval=20, maxval=250, group='Calibration')
i_target    = input.float(0.72, 'Target Containment', minval=0.50, maxval=0.95, step=0.01, group='Calibration')
i_decay     = input.float(0.985, 'Calibration Decay', minval=0.95, maxval=1.0, step=0.005, group='Calibration')"""
code = code.replace(old_inputs, new_inputs)

# 3. Add Quantile function
quantile_func = """// ================================================================
// F_QUANTILE (PINE SAFE)
// ================================================================
f_quantile(float[] src, float q, float fallback) =>
    int size = array.size(src)
    if size == 0
        fallback
    else
        float[] temp = array.copy(src)
        array.sort(temp, order.ascending)
        int index = int(math.ceil(q * size)) - 1
        index := math.max(0, math.min(size - 1, index))
        array.get(temp, index)

"""
code = code.replace("// ================================================================\n// F2:", quantile_func + "// ================================================================\n// F2:")

# 4. Replace Predicted Range variables
old_pred_vars = """var float _pred_hi    = na
var float _pred_lo    = na
var float _pred_anch  = na
var float _pred_width = na
var float[] _contain_hist = array.new_float(0)
var float _auto_sigma_adj = 1.0
i_auto_sigma = input.bool(false, 'Auto-Calibrate Sigma', group='Range', tooltip='Automatically adjusts sigma to maintain ~72% historical containment rate. Overrides manual Sigma when enabled.')
var float _us_norm_p  = 1.0   // persisted upper semivariance scalar
var float _ls_norm_p  = 1.0   // persisted lower semivariance scalar
var float _bm_sess    = na    // base move locked at session open
var float _prev_cons  = 0.0   // previous bar consumption for velocity
float _eff_sigma = i_auto_sigma ? i_sigma * _auto_sigma_adj : i_sigma"""

new_pred_vars = """var float _pred_hi    = na
var float _pred_lo    = na
var float _pred_anch  = na
var float _pred_width = na

var float[] _up_ratio_hist = array.new_float()
var float[] _dn_ratio_hist = array.new_float()
var float _raw_up_ref = na
var float _raw_dn_ref = na
var float _cal_up     = na
var float _cal_dn     = na
var float _preset_sigma = na

var float _us_norm_p  = 1.0   
var float _ls_norm_p  = 1.0   
var float _bm_sess    = na    
var float _prev_cons  = 0.0"""
code = code.replace(old_pred_vars, new_pred_vars)

# 5. Session First Bar
old_sess_first = """    float _var_ratio = _rv_m > 1e-12 ? math.sqrt(math.max(_hv_eff, 1e-10) / _rv_m) : 1.0
    float _half_range = nz(_avg_range, _pred_anch * math.sqrt(math.max(_hv_eff, 1e-10)) * 2.0) * 0.5 * _var_ratio * _eff_sigma
    float _us_norm = _us / math.max((_us + _ls) * 0.5, 1e-6)
    float _ls_norm = _ls / math.max((_us + _ls) * 0.5, 1e-6)
    _us_norm_p  := _us_norm
    _ls_norm_p  := _ls_norm
    _bm_sess    := nz(_avg_range, _pred_anch * math.sqrt(math.max(_hv_eff, 1e-10)) * 2.0) * 0.5 * _var_ratio
    _pred_hi    := _pred_anch + _half_range * _us_norm
    _pred_lo    := _pred_anch - _half_range * _ls_norm
    _pred_width := _pred_hi - _pred_lo
    _prev_cons  := 0.0"""

new_sess_first = """    float _var_ratio = _rv_m > 1e-12 ? math.sqrt(math.max(_hv_eff, 1e-10) / _rv_m) : 1.0
    float _us_norm = _us / math.max((_us + _ls) * 0.5, 1e-6)
    float _ls_norm = _ls / math.max((_us + _ls) * 0.5, 1e-6)
    _us_norm_p  := _us_norm
    _ls_norm_p  := _ls_norm
    _bm_sess    := nz(_avg_range, _pred_anch * math.sqrt(math.max(_hv_eff, 1e-10)) * 2.0) * 0.5 * _var_ratio
    
    string tk = syminfo.ticker
    _preset_sigma := tk == 'NIFTY' ? 1.57 : tk == 'BANKNIFTY' ? 1.80 : tk == 'SENSEX' ? 1.85 : tk == 'CNXFINANCE' or tk == 'FINNIFTY' ? 1.81 : tk == 'NIFTYJR' or tk == 'MIDCPNIFTY' ? 1.89 : tk == 'BTCUSDT' ? 2.22 : 1.50
    
    float _conf_up = f_quantile(_up_ratio_hist, i_target, _preset_sigma)
    float _conf_dn = f_quantile(_dn_ratio_hist, i_target, _preset_sigma)
    
    bool _enough_hist = array.size(_up_ratio_hist) >= 20
    _cal_up := i_adapt_cal and _enough_hist ? _conf_up : _preset_sigma
    _cal_dn := i_adapt_cal and _enough_hist ? _conf_dn : _preset_sigma
    
    float _raw_up_half = _bm_sess * _us_norm_p
    float _raw_dn_half = _bm_sess * _ls_norm_p
    _raw_up_ref := _raw_up_half
    _raw_dn_ref := _raw_dn_half
    
    _pred_hi    := _pred_anch + _raw_up_half * _cal_up
    _pred_lo    := _pred_anch - _raw_dn_half * _cal_dn
    _pred_width := _pred_hi - _pred_lo
    _prev_cons  := 0.0"""
code = code.replace(old_sess_first, new_sess_first)

# 6. Not intra 
old_not_intra = """    float _var_ratio = _rv_m > 1e-12 ? math.sqrt(math.max(_hv_eff, 1e-10) / _rv_m) : 1.0
    float _half_range = nz(_avg_range, _pred_anch * math.sqrt(math.max(_hv_eff, 1e-10)) * 2.0) * 0.5 * _var_ratio * _eff_sigma
    float _us_norm = _us / math.max((_us + _ls) * 0.5, 1e-6)
    float _ls_norm = _ls / math.max((_us + _ls) * 0.5, 1e-6)
    _pred_hi    := _pred_anch + _half_range * _us_norm
    _pred_lo    := _pred_anch - _half_range * _ls_norm
    _pred_width := _pred_hi - _pred_lo"""

new_not_intra = """    float _var_ratio = _rv_m > 1e-12 ? math.sqrt(math.max(_hv_eff, 1e-10) / _rv_m) : 1.0
    float _us_norm = _us / math.max((_us + _ls) * 0.5, 1e-6)
    float _ls_norm = _ls / math.max((_us + _ls) * 0.5, 1e-6)
    _bm_sess    := nz(_avg_range, _pred_anch * math.sqrt(math.max(_hv_eff, 1e-10)) * 2.0) * 0.5 * _var_ratio
    
    string tk = syminfo.ticker
    _preset_sigma := tk == 'NIFTY' ? 1.57 : tk == 'BANKNIFTY' ? 1.80 : tk == 'SENSEX' ? 1.85 : tk == 'CNXFINANCE' or tk == 'FINNIFTY' ? 1.81 : tk == 'NIFTYJR' or tk == 'MIDCPNIFTY' ? 1.89 : tk == 'BTCUSDT' ? 2.22 : 1.50
    _cal_up := _preset_sigma
    _cal_dn := _preset_sigma
    
    float _raw_up_half = _bm_sess * _us_norm
    float _raw_dn_half = _bm_sess * _ls_norm
    
    _pred_hi    := _pred_anch + _raw_up_half * _cal_up
    _pred_lo    := _pred_anch - _raw_dn_half * _cal_dn
    _pred_width := _pred_hi - _pred_lo"""
code = code.replace(old_not_intra, new_not_intra)

# 7. Self-Calibrating -> Walk Forward
old_calib = """// ================================================================
// SELF-CALIBRATING SIGMA — rolling containment history
// At session end, records whether the range contained price.
// Adjusts sigma toward target containment (72%).
// ================================================================
if _intra and session.islastbar and _pred_width > 0
    bool _contained = _sess_hi <= _pred_hi and _sess_lo >= _pred_lo
    array.push(_contain_hist, _contained ? 1.0 : 0.0)
    if array.size(_contain_hist) > 22
        array.shift(_contain_hist)
    if array.size(_contain_hist) >= 10
        float _contain_rate = array.avg(_contain_hist)
        // Target: 72% containment. If too high -> sigma too wide -> narrow.
        // If too low -> sigma too narrow -> widen. Step: 2% per session.
        if _contain_rate > 0.80
            _auto_sigma_adj := math.max(_auto_sigma_adj * 0.98, 0.5)
        else if _contain_rate < 0.65
            _auto_sigma_adj := math.min(_auto_sigma_adj * 1.02, 2.0)"""

new_calib = """// ================================================================
// WALK-FORWARD CALIBRATION HISTORY UPDATE
// ================================================================
if _intra and session.islastbar and _pred_width > 0
    float _up_ratio = math.max(_sess_hi - _pred_anch, 0) / math.max(_raw_up_ref, 1e-9)
    float _dn_ratio = math.max(_pred_anch - _sess_lo, 0) / math.max(_raw_dn_ref, 1e-9)
    array.push(_up_ratio_hist, _up_ratio)
    array.push(_dn_ratio_hist, _dn_ratio)
    if array.size(_up_ratio_hist) > i_cal_len
        array.shift(_up_ratio_hist)
    if array.size(_dn_ratio_hist) > i_cal_len
        array.shift(_dn_ratio_hist)"""
code = code.replace(old_calib, new_calib)

# 8. Dynamic Cone variables
old_cone = """float _hurst_exp      = math.max(_H, 0.1)
float _remaining_half = _intra and not na(_bm_sess) ? _bm_sess * _eff_sigma * math.pow(_rem_var_frac, _hurst_exp) * _or_adj : na
float _inner_hi       = _intra and not na(_remaining_half) ? close + _remaining_half * _us_norm_p : na
float _inner_lo       = _intra and not na(_remaining_half) ? close - _remaining_half * _ls_norm_p : na
float _remaining_pts  = _intra and not na(_remaining_half) ? (_remaining_half * (_us_norm_p + _ls_norm_p)) : na"""

new_cone = """float _hurst_exp      = math.max(_H, 0.1)
float _remaining_up   = _intra and not na(_bm_sess) ? _bm_sess * _cal_up * math.pow(_rem_var_frac, _hurst_exp) * _or_adj : na
float _remaining_dn   = _intra and not na(_bm_sess) ? _bm_sess * _cal_dn * math.pow(_rem_var_frac, _hurst_exp) * _or_adj : na
float _inner_hi       = _intra and not na(_remaining_up) ? close + _remaining_up * _us_norm_p : na
float _inner_lo       = _intra and not na(_remaining_dn) ? close - _remaining_dn * _ls_norm_p : na
float _remaining_pts  = _intra and not na(_remaining_up) ? (_remaining_up * _us_norm_p + _remaining_dn * _ls_norm_p) : na"""
code = code.replace(old_cone, new_cone)

# 9. Regime & Breach Prob
old_regime = """// Regime: activate at 33% elapsed (not 50%) for earlier 0DTE signal
bool _past_third = _sess_fraction >= 0.33
string _regime = _intra ? (_past_third ? (_consumed_pct < 35 ? 'CONSOLIDATING' : _consumed_pct > 65 ? 'TRENDING' : 'NORMAL') : 'ACCUMULATING') : 'DAILY'"""

code = code.replace(old_regime, "")

old_breach = """// ================================================================
// BREACH PROBABILITY  [NEW — empirical estimate]
// Based on current consumption level and session fraction elapsed.
// Calibrated from 1630-session simulation (NIFTY + BANKNIFTY).
// ================================================================
float _breach_prob = na
if _intra and not na(_consumed_pct)
    if _consumed_pct > 85
        _breach_prob := _sess_fraction < 0.5 ? 78.0 : 55.0
    else if _consumed_pct > 65
        _breach_prob := _sess_fraction < 0.5 ? 52.0 : 35.0
    else if _consumed_pct > 45
        _breach_prob := _sess_fraction < 0.5 ? 30.0 : 18.0
    else if _consumed_pct > 25
        _breach_prob := _sess_fraction < 0.5 ? 18.0 : 10.0
    else
        _breach_prob := 8.0"""

new_breach_regime = """// ================================================================
// BREACH PROBABILITY
// ================================================================
float _breach_prob = na
if _intra and not na(_consumed_pct)
    string tk = syminfo.ticker
    float _preset_breach = tk == 'NIFTY' ? 34.27 : tk == 'BANKNIFTY' ? 35.73 : tk == 'SENSEX' ? 40.24 : tk == 'CNXFINANCE' or tk == 'FINNIFTY' ? 37.80 : tk == 'NIFTYJR' or tk == 'MIDCPNIFTY' ? 39.15 : tk == 'BTCUSDT' ? 28.95 : 35.00
    
    float _dist_up = (_pred_hi - close) / math.max(_pred_width, 1e-9)
    float _dist_dn = (close - _pred_lo) / math.max(_pred_width, 1e-9)
    float _nearest_dist = math.min(_dist_up, _dist_dn)
    
    float _cons_adj = _consumed_pct > 100 ? 35 : _consumed_pct > 85 ? 24 : _consumed_pct > 65 ? 12 : _consumed_pct > 45 ? 3 : _consumed_pct > 25 ? -6 : -15
    float _time_adj = _sess_fraction < 0.33 ? -8 : _sess_fraction > 0.66 ? 6 : 0
    float _vel_adj = _cons_velocity > 12 ? 8 : _cons_velocity > 6 ? 4 : (_cons_velocity < 1 and _sess_fraction > 0.5) ? -5 : 0
    float _dist_adj = _nearest_dist < 0.05 ? 15 : _nearest_dist < 0.10 ? 9 : _nearest_dist < 0.20 ? 4 : _nearest_dist > 0.35 ? -6 : 0
    float _hurst_adj = _H > 0.56 ? 5 : _H < 0.44 ? -4 : 0
    
    float _vov_med = ta.median(_vov, 22)
    float _vov_adj = _vov > _vov_med * 1.2 ? 4 : 0
    float _jump_adj = _jfl > 0.5 ? 6 : 0
    
    _breach_prob := math.max(3, math.min(95, _preset_breach + _cons_adj + _time_adj + _vel_adj + _dist_adj + _hurst_adj + _vov_adj + _jump_adj))

// ================================================================
// REGIME CLASSIFICATION
// ================================================================
bool _past_third = _sess_fraction >= 0.33
string _regime = 'DAILY'
if _intra
    bool _breach_cond = close > _pred_hi or close < _pred_lo
    float _dist_up_r = (_pred_hi - close) / math.max(_pred_width, 1e-9)
    float _dist_dn_r = (close - _pred_lo) / math.max(_pred_width, 1e-9)
    float _nearest_dist_r = math.min(_dist_up_r, _dist_dn_r)
    bool _pressure_cond = (not _breach_cond and _nearest_dist_r < 0.10) or nz(_breach_prob, 0) > 65
    bool _trend_cond = _consumed_pct > 65 or _cons_velocity > 12 or (_H > 0.56 and _consumed_pct > 55)
    bool _consol_cond = _consumed_pct < 35 and _cons_velocity < 3 and nz(_breach_prob, 0) < 30 and _past_third
    
    _regime := _breach_cond ? 'BREACH' : _pressure_cond ? 'PRESSURE' : _trend_cond ? 'TRENDING' : _consol_cond ? 'CONSOLIDATING' : not _past_third ? 'ACCUMULATING' : 'NORMAL'"""
code = code.replace(old_breach, new_breach_regime)

# 10. Update Model Confidence
confidence_block = """// ================================================================
// MODEL CONFIDENCE
// ================================================================
float _confidence = 100
if array.size(_up_ratio_hist) < 20
    _confidence -= 20
bool _ols_active = math.abs(_bd - 0.36) > 1e-9 or math.abs(_bw - 0.28) > 1e-9 or math.abs(_bm - 0.28) > 1e-9
if not _ols_active
    _confidence -= 10
if nz(_preset_sigma, 1.50) == 1.50
    _confidence -= 8
if _is_nse and na(_vix_raw)
    _confidence -= 8
if not _intra
    _confidence -= 10
if _H <= 0.35 or _H >= 0.65
    _confidence -= 10
float _cal_div = math.max(nz(_cal_up, 1.0) / math.max(nz(_cal_dn, 1.0), 1e-9), nz(_cal_dn, 1.0) / math.max(nz(_cal_up, 1.0), 1e-9))
if _cal_div > 1.8
    _confidence -= 8
_confidence := math.max(0, math.min(100, _confidence))

// ================================================================
// MODEL STATE TABLE
// ================================================================
"""
code = code.replace("// ================================================================\n// MODEL STATE TABLE\n// ================================================================", confidence_block)

# Update colors for regimes
old_colors = """color c_consolidating = color.rgb(40, 140, 255)
color c_trending = color.rgb(255, 50, 80)
color c_normal = color.rgb(180, 180, 190)"""
new_colors = """color c_breach = color.rgb(255, 30, 60)
color c_pressure = color.rgb(255, 120, 0)
color c_consolidating = color.rgb(40, 140, 255)
color c_trending = color.rgb(255, 50, 80)
color c_normal = color.rgb(180, 180, 190)"""
code = code.replace(old_colors, new_colors)

# Update labels 
old_reg_lbl = """    string r_txt = _regime == 'CONSOLIDATING' ? '🔵 CONSOL\\n' + str.tostring(_consumed_pct, '#.#') + '%' :
                   _regime == 'TRENDING' ? '🔴 TREND\\n' + str.tostring(_consumed_pct, '#.#') + '%' :
                   '⚪ NORMAL\\n' + str.tostring(_consumed_pct, '#.#') + '%'
    color r_col = _regime == 'CONSOLIDATING' ? c_consolidating :
                  _regime == 'TRENDING' ? c_trending : c_normal"""

new_reg_lbl = """    string r_txt = _regime == 'BREACH' ? '⛔ BREACH\\n' + str.tostring(_consumed_pct, '#.#') + '%' :
                   _regime == 'PRESSURE' ? '🟠 PRESSURE\\n' + str.tostring(_consumed_pct, '#.#') + '%' :
                   _regime == 'CONSOLIDATING' ? '🔵 CONSOL\\n' + str.tostring(_consumed_pct, '#.#') + '%' :
                   _regime == 'TRENDING' ? '🔴 TREND\\n' + str.tostring(_consumed_pct, '#.#') + '%' :
                   '⚪ NORMAL\\n' + str.tostring(_consumed_pct, '#.#') + '%'
    color r_col = _regime == 'BREACH' ? c_breach :
                  _regime == 'PRESSURE' ? c_pressure :
                  _regime == 'CONSOLIDATING' ? c_consolidating :
                  _regime == 'TRENDING' ? c_trending : c_normal"""
code = code.replace(old_reg_lbl, new_reg_lbl)

# Update bg
old_bg = """color _regime_bg = _intra and _past_third ? (_regime == 'CONSOLIDATING' ? color.new(c_consolidating, 95) : _regime == 'TRENDING' ? color.new(c_trending, 95) : na) : na"""
new_bg = """color _regime_bg = _intra and _past_third ? (_regime == 'BREACH' ? color.new(c_breach, 95) : _regime == 'PRESSURE' ? color.new(c_pressure, 95) : _regime == 'CONSOLIDATING' ? color.new(c_consolidating, 95) : _regime == 'TRENDING' ? color.new(c_trending, 95) : na) : na"""
code = code.replace(old_bg, new_bg)

# Cone strike replacement
old_cone_strike = """float _si = float(_strike_int)
if i_strikes and _intra and not na(_remaining_half)
    float _cone_up = close + _remaining_half * _us_norm_p
    float _cone_dn = close - _remaining_half * _ls_norm_p
    _sig1_hi := math.round(_cone_up / _si) * _si
    _sig1_lo := math.round(_cone_dn / _si) * _si"""

new_cone_strike = """float _si = float(_strike_int)
if i_strikes and _intra and not na(_remaining_up)
    float _cone_up = close + _remaining_up * _us_norm_p
    float _cone_dn = close - _remaining_dn * _ls_norm_p
    _sig1_hi := math.round(_cone_up / _si) * _si
    _sig1_lo := math.round(_cone_dn / _si) * _si"""
code = code.replace(old_cone_strike, new_cone_strike)

# Table details
old_table_state = """    color _reg_col = _regime == 'CONSOLIDATING' ? c_consolidating :
                     _regime == 'TRENDING' ? c_trending :
                     _regime == 'ACCUMULATING' ? color.rgb(255, 170, 0) : c_normal
    string _reg_sig = _regime == 'CONSOLIDATING' ? '🔵 CONSOL · Sell Prem' :
                      _regime == 'TRENDING' ? '🔴 TREND · Direction' :
                      _regime == 'ACCUMULATING' ? '⏳ ACCUM' :
                      _regime == 'DAILY' ? '📊 DAILY' : '⚪ NORMAL'
    f_row(_T, 0, 'REGIME', _reg_sig, _reg_col)"""

new_table_state = """    color _reg_col = _regime == 'BREACH' ? c_breach :
                     _regime == 'PRESSURE' ? c_pressure :
                     _regime == 'CONSOLIDATING' ? c_consolidating :
                     _regime == 'TRENDING' ? c_trending :
                     _regime == 'ACCUMULATING' ? color.rgb(255, 170, 0) : c_normal
    string _reg_sig = _regime == 'BREACH' ? '⛔ BREACH · Risk Off' :
                      _regime == 'PRESSURE' ? '🟠 PRESSURE · Edge Risk' :
                      _regime == 'CONSOLIDATING' ? '🔵 CONSOL · Sell Prem' :
                      _regime == 'TRENDING' ? '🔴 TREND · Direction' :
                      _regime == 'ACCUMULATING' ? '⏳ ACCUM' :
                      _regime == 'DAILY' ? '📊 DAILY' : '⚪ NORMAL'
    f_row(_T, 0, 'REGIME', _reg_sig, _reg_col)
    
    color _conf_col = _confidence >= 80 ? color.rgb(0, 220, 160) : _confidence >= 60 ? color.rgb(255, 170, 0) : color.rgb(255, 50, 80)
    f_row(_T, 1, 'CONFIDENCE', str.tostring(_confidence, '#') + '%', _conf_col)"""

code = code.replace(old_table_state, new_table_state)

old_table_cpc = """    f_row(_T, 1, 'CONSUMED', na(_consumed_pct) ? '—' : str.tostring(_consumed_pct, '#.#') + '%', _cpc)"""
new_table_cpc = """    f_row(_T, 2, 'CONSUMED', na(_consumed_pct) ? '—' : str.tostring(_consumed_pct, '#.#') + '%', _cpc)"""
code = code.replace(old_table_cpc, new_table_cpc)

old_table_rows = """    f_row(_T, 2, 'RANGE', '±' + str.tostring(_pts, '#.#') + '  (' + str.tostring(_n_strikes) + ' stk)', color.rgb(230, 230, 240))

    f_row(_T, 3, 'Remaining', na(_remaining_pts) ? '—' : str.tostring(_remaining_pts, '#.#') + ' pts', c_cone)

    color _bpc = na(_breach_prob) ? c_normal : _breach_prob > 50 ? color.rgb(255, 50, 80) : _breach_prob > 25 ? color.rgb(255, 170, 0) : color.rgb(0, 220, 160)
    f_row(_T, 4, 'Breach %', na(_breach_prob) ? '—' : str.tostring(_breach_prob, '#.#') + '%', _bpc)

    f_row(_T, 5, 'HAR Vol', str.tostring(_ann, '#.##') + '%', color.rgb(255, 191, 36))"""

new_table_rows = """    f_row(_T, 3, 'RANGE', '±' + str.tostring(_pts, '#.#') + '  (' + str.tostring(_n_strikes) + ' stk)', color.rgb(230, 230, 240))
    f_row(_T, 4, 'Remaining', na(_remaining_pts) ? '—' : str.tostring(_remaining_pts, '#.#') + ' pts', c_cone)
    
    color _bpc = na(_breach_prob) ? c_normal : _breach_prob > 50 ? color.rgb(255, 50, 80) : _breach_prob > 25 ? color.rgb(255, 170, 0) : color.rgb(0, 220, 160)
    f_row(_T, 5, 'Breach %', na(_breach_prob) ? '—' : str.tostring(_breach_prob, '#.#') + '%', _bpc)

    f_row(_T, 6, 'Preset Sig', str.tostring(nz(_preset_sigma, 0.0), '#.##'), color.rgb(60, 130, 220))
    f_row(_T, 7, 'UP Cal', str.tostring(nz(_cal_up, 0.0), '#.##'), color.rgb(60, 130, 220))
    f_row(_T, 8, 'DN Cal', str.tostring(nz(_cal_dn, 0.0), '#.##'), color.rgb(60, 130, 220))

    f_row(_T, 9, 'HAR Vol', str.tostring(_ann, '#.##') + '%', color.rgb(255, 191, 36))"""
code = code.replace(old_table_rows, new_table_rows)

# Shift all the rest down
old_t6 = """    color _hcol = _H > 0.52 ? color.rgb(255, 30, 80) : _H < 0.48 ? color.rgb(0, 220, 160) : c_normal
    f_row(_T, 6, 'Hurst', str.tostring(_H, '#.###'), _hcol)

    f_row(_T, 7, 'β d/w/m', str.tostring(_bd, '#.##') + ' / ' + str.tostring(_bw, '#.##') + ' / ' + str.tostring(_bm, '#.##'), c_normal)

    color _dcol = _df > 1.2 ? color.rgb(255, 170, 0) : _df < 0.8 ? color.rgb(0, 220, 160) : c_normal
    f_row(_T, 8, 'Diurnal', str.tostring(_df, '#.##'), _dcol)

    color _rcol = _react_ratio > 1.15 ? color.rgb(255, 100, 80) : _react_ratio < 0.85 ? color.rgb(0, 200, 160) : c_normal
    f_row(_T, 9, 'React', str.tostring(_react_ratio, '#.##') + '×', _rcol)

    if _is_nse and i_vix and not na(_vix_raw)
        f_row(_T, 10, 'India VIX', str.tostring(_vix_raw, '#.##') + '%', color.rgb(255, 191, 36))
        color _ivrc = _iv_rv_factor > 1.15 ? color.rgb(255, 100, 80) : _iv_rv_factor < 0.85 ? color.rgb(0, 200, 160) : c_normal
        f_row(_T, 11, 'IV/RV', str.tostring(_iv_rv_factor, '#.##') + '×', _ivrc)
    else
        f_row(_T, 10, 'India VIX', _is_nse ? '—' : 'N/A', c_normal)
        f_row(_T, 11, 'IV/RV', '1.00×', c_normal)

    string _sig_txt = i_auto_sigma ? str.tostring(_eff_sigma, '#.##') + 'σ (auto)' : str.tostring(i_sigma, '#.##') + 'σ'
    f_row(_T, 12, 'Sigma', _sig_txt, color.rgb(60, 130, 220))
    f_row(_T, 13, 'Anchor', str.tostring(nz(_pred_anch, 0.0), '#.##'), color.rgb(255, 191, 36))

    bool _ols = math.abs(_bd - 0.36) > 1e-9 or math.abs(_bw - 0.28) > 1e-9 or math.abs(_bm - 0.28) > 1e-9
    f_row(_T, 14, 'OLS', _ols ? 'Active' : 'Warmup', _ols ? color.rgb(0, 220, 160) : color.rgb(255, 170, 0))"""

new_t10 = """    color _hcol = _H > 0.52 ? color.rgb(255, 30, 80) : _H < 0.48 ? color.rgb(0, 220, 160) : c_normal
    f_row(_T, 10, 'Hurst', str.tostring(_H, '#.###'), _hcol)

    f_row(_T, 11, 'β d/w/m', str.tostring(_bd, '#.##') + ' / ' + str.tostring(_bw, '#.##') + ' / ' + str.tostring(_bm, '#.##'), c_normal)

    color _dcol = _df > 1.2 ? color.rgb(255, 170, 0) : _df < 0.8 ? color.rgb(0, 220, 160) : c_normal
    f_row(_T, 12, 'Diurnal', str.tostring(_df, '#.##'), _dcol)

    color _rcol = _react_ratio > 1.15 ? color.rgb(255, 100, 80) : _react_ratio < 0.85 ? color.rgb(0, 200, 160) : c_normal
    f_row(_T, 13, 'React', str.tostring(_react_ratio, '#.##') + '×', _rcol)

    if _is_nse and i_vix and not na(_vix_raw)
        f_row(_T, 14, 'India VIX', str.tostring(_vix_raw, '#.##') + '%', color.rgb(255, 191, 36))
    else
        f_row(_T, 14, 'India VIX', _is_nse ? '—' : 'N/A', c_normal)"""
code = code.replace(old_t6, new_t10)

# 14. Logs
old_log1 = """if i_log and barstate.isfirst
    log.info('time_ms,symbol,tf,close,anchor,har_vol%,hurst_H,sem_up,sem_down,vov%,jump_vol%,jump_flag,beta_d,beta_w,beta_m,diurnal_bk,diurnal_df,base_move,exp_move,band_hi,band_lo,outer_hi,outer_lo,consumed_pct,regime,pred_hi,pred_lo,sess_hi,sess_lo,remaining_pts,breach_prob,cons_velocity')

if i_log and barstate.isconfirmed
    float _log_ann  = math.sqrt(math.max(_hv, 0.0) * 252.0) * 100.0
    float _log_jann = math.sqrt(math.max(_jv, 0.0) * 252.0) * 100.0
    float _log_vann = _vov * math.sqrt(252.0) * 100.0
    float _log_pts  = nz(_pred_width, 0.0) * 0.5
    int   _log_bk   = f_bucket()
    string _csv =
         str.tostring(time)                         + ',' +
         syminfo.ticker                              + ',' +
         timeframe.period                            + ',' +
         str.tostring(close,         '#.##')         + ',' +
         str.tostring(_pred_anch,    '#.##')         + ',' +
         str.tostring(_log_ann,      '#.##')         + ',' +
         str.tostring(_H,            '#.####')       + ',' +
         str.tostring(_us,           '#.####')       + ',' +
         str.tostring(_ls,           '#.####')       + ',' +
         str.tostring(_log_vann,     '#.##')         + ',' +
         str.tostring(_log_jann,     '#.##')         + ',' +
         (_jfl > 0.5 ? '1' : '0')                   + ',' +
         str.tostring(_bd,           '#.####')       + ',' +
         str.tostring(_bw,           '#.####')       + ',' +
         str.tostring(_bm,           '#.####')       + ',' +
         str.tostring(_log_bk)                       + ',' +
         str.tostring(_df,           '#.####')       + ',' +
         str.tostring(_base_move,    '#.##')         + ',' +
         str.tostring(_log_pts,      '#.#')          + ',' +
         str.tostring(_pred_hi,      '#.##')         + ',' +
         str.tostring(_pred_lo,      '#.##')         + ',' +
         str.tostring(na,            '#.##')         + ',' +
         str.tostring(na,            '#.##')         + ',' +
         str.tostring(_consumed_pct, '#.##')         + ',' +
         _regime                                       + ',' +
         str.tostring(_pred_hi,      '#.##')         + ',' +
         str.tostring(_pred_lo,      '#.##')         + ',' +
         str.tostring(_sess_hi,      '#.##')         + ',' +
         str.tostring(_sess_lo,      '#.##')         + ',' +
         str.tostring(_remaining_pts,'#.##')         + ',' +
         str.tostring(_breach_prob,  '#.##')         + ',' +
         str.tostring(_cons_velocity,'#.##')"""

new_log1 = """if i_log and barstate.isfirst
    log.info('time_ms,symbol,preset,tf,strike_step,session_min,close,anchor,pred_hi,pred_lo,raw_up_half,raw_dn_half,cal_up,cal_dn,target_containment,cal_sessions,model_confidence,har_vol%,hurst_H,sem_up,sem_down,vov%,jump_vol%,jump_flag,beta_d,beta_w,beta_m,diurnal_bk,diurnal_df,base_move,remaining_up,remaining_dn,consumed_pct,cons_velocity,nearest_band_dist,breach_prob,regime,sess_hi,sess_lo')

if i_log and barstate.isconfirmed
    float _log_ann  = math.sqrt(math.max(_hv, 0.0) * 252.0) * 100.0
    float _log_jann = math.sqrt(math.max(_jv, 0.0) * 252.0) * 100.0
    float _log_vann = _vov * math.sqrt(252.0) * 100.0
    int   _log_bk   = f_bucket()
    
    float _dist_up_log = (_pred_hi - close) / math.max(_pred_width, 1e-9)
    float _dist_dn_log = (close - _pred_lo) / math.max(_pred_width, 1e-9)
    float _nearest_dist_log = math.min(_dist_up_log, _dist_dn_log)

    string _csv =
         str.tostring(time)                         + ',' +
         syminfo.ticker                              + ',' +
         str.tostring(_preset_sigma, '#.##')         + ',' +
         timeframe.period                            + ',' +
         str.tostring(_strike_int)                   + ',' +
         str.tostring(i_sess)                        + ',' +
         str.tostring(close,         '#.##')         + ',' +
         str.tostring(_pred_anch,    '#.##')         + ',' +
         str.tostring(_pred_hi,      '#.##')         + ',' +
         str.tostring(_pred_lo,      '#.##')         + ',' +
         str.tostring(_raw_up_ref,   '#.##')         + ',' +
         str.tostring(_raw_dn_ref,   '#.##')         + ',' +
         str.tostring(_cal_up,       '#.##')         + ',' +
         str.tostring(_cal_dn,       '#.##')         + ',' +
         str.tostring(i_target,      '#.##')         + ',' +
         str.tostring(array.size(_up_ratio_hist))    + ',' +
         str.tostring(_confidence,   '#.##')         + ',' +
         str.tostring(_log_ann,      '#.##')         + ',' +
         str.tostring(_H,            '#.####')       + ',' +
         str.tostring(_us,           '#.####')       + ',' +
         str.tostring(_ls,           '#.####')       + ',' +
         str.tostring(_log_vann,     '#.##')         + ',' +
         str.tostring(_log_jann,     '#.##')         + ',' +
         (_jfl > 0.5 ? '1' : '0')                   + ',' +
         str.tostring(_bd,           '#.####')       + ',' +
         str.tostring(_bw,           '#.####')       + ',' +
         str.tostring(_bm,           '#.####')       + ',' +
         str.tostring(_log_bk)                       + ',' +
         str.tostring(_df,           '#.####')       + ',' +
         str.tostring(_base_move,    '#.##')         + ',' +
         str.tostring(nz(_remaining_up, 0.0), '#.##')+ ',' +
         str.tostring(nz(_remaining_dn, 0.0), '#.##')+ ',' +
         str.tostring(_consumed_pct, '#.##')         + ',' +
         str.tostring(_cons_velocity,'#.##')         + ',' +
         str.tostring(_nearest_dist_log, '#.####')   + ',' +
         str.tostring(_breach_prob,  '#.##')         + ',' +
         _regime                                     + ',' +
         str.tostring(_sess_hi,      '#.##')         + ',' +
         str.tostring(_sess_lo,      '#.##')"""
code = code.replace(old_log1, new_log1)

with open(out_file, "w") as f:
    f.write(code)
print("Migration completed successfully.")
