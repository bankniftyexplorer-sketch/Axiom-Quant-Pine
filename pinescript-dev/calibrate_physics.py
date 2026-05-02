import pandas as pd
import numpy as np
from itertools import product
from scipy.stats import spearmanr

def load_pine_log(filepath):
    df_raw = pd.read_csv(filepath)
    # The 'Message' column contains the nested CSV
    # The first row of 'Message' has the headers
    headers = df_raw.iloc[0]['Message'].split(',')
    
    data = []
    for msg in df_raw.iloc[1:]['Message']:
        if pd.notna(msg):
            data.append(msg.split(','))
            
    df = pd.DataFrame(data, columns=headers)
    df['Datetime'] = pd.to_datetime(df['Datetime'])
    df = df.set_index('Datetime')
    
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df

def generate_ground_truth(df, index_name='BANKNIFTY'):
    close_col = f'{index_name}_C'
    returns = df[close_col].pct_change()
    
    labels = np.zeros(len(df))
    # Thresholds for ground truth
    # ±2: strong acceleration (> 0.1% return in 5min)
    # ±1: mild grind (0.03% to 0.1%)
    # 0: flat (< 0.03%)
    
    for i, ret in enumerate(returns):
        if pd.isna(ret):
            continue
        if ret > 0.001:
            labels[i] = 2
        elif ret > 0.0003:
            labels[i] = 1
        elif ret < -0.001:
            labels[i] = -2
        elif ret < -0.0003:
            labels[i] = -1
        else:
            labels[i] = 0
            
    return labels

def f_cum_log_ret(prices):
    lr = np.zeros(len(prices))
    for i in range(1, len(prices)):
        if prices[i] > 0 and prices[i-1] > 0:
            lr[i] = np.log(prices[i] / prices[i-1])
    return np.cumsum(lr)

def f_structural_score(p, _dz):
    score = np.zeros(len(p))
    d1_out = np.zeros(len(p))
    
    _eps = 1e-6
    
    for i in range(len(p)):
        if i < 10:
            continue
            
        d1 = p[i] - p[i-1]
        d2 = p[i] - 2*p[i-1] + p[i-2]
        d3 = p[i] - 3*p[i-1] + 3*p[i-2] - p[i-3]
        d4 = p[i] - 4*p[i-1] + 6*p[i-2] - 4*p[i-3] + p[i-4]
        
        d2_e = p[i] - 2*p[i-2] + p[i-4]
        d2_o = p[i-1] - 2*p[i-3] + p[i-5]
        d3_e = p[i] - 3*p[i-2] + 3*p[i-4] - p[i-6]
        d3_o = p[i-1] - 3*p[i-3] + 3*p[i-5] - p[i-7]
        
        d1_x = p[i] - p[i-1] - p[i-2] + p[i-3]
        d2_x = p[i] - p[i-1] - 2*p[i-2] + 2*p[i-3] + p[i-4] - p[i-5]
        convex = 2*p[i] - p[i-1] - p[i-2]
        
        E2_1 = d2 / max(abs(d1), _eps)
        E4_3 = d4 / max(abs(d3), _eps)
        
        E2_1_prev = (p[i-1] - 2*p[i-2] + p[i-3]) / max(abs(p[i-1] - p[i-2]), _eps)
        E4_3_prev = (p[i-1] - 4*p[i-2] + 6*p[i-3] - 4*p[i-4] + p[i-5]) / max(abs(p[i-1] - 3*p[i-2] + 3*p[i-3] - p[i-4]), _eps)
        
        s = 0.0
        s += 0.0 if abs(d1) < _dz else (1.0 if d1 >= 0 else -1.0)
        s += 0.0 if abs(d1_x) < _dz else (1.0 if d1_x >= 0 else -1.0)
        s += 0.0 if abs(d2) < _dz else (2.0 if d2 >= 0 else -2.0)
        s += 0.0 if abs(d2_e) < _dz else (2.0 if d2_e >= 0 else -2.0)
        s += 0.0 if abs(d2_o) < _dz else (2.0 if d2_o >= 0 else -2.0)
        s += 0.0 if abs(d2_x) < _dz else (2.0 if d2_x >= 0 else -2.0)
        s += 0.0 if abs(convex) < _dz else (2.0 if convex >= 0 else -2.0)
        s += 0.0 if abs(d3) < _dz else (3.0 if d3 >= 0 else -3.0)
        s += 0.0 if abs(d3_e) < _dz else (3.0 if d3_e >= 0 else -3.0)
        s += 0.0 if abs(d3_o) < _dz else (3.0 if d3_o >= 0 else -3.0)
        s += 0.0 if abs(d4) < _dz else (4.0 if d4 >= 0 else -4.0)
        
        s += 1.0 if E2_1 >= E2_1_prev else -1.0
        s += 1.0 if E4_3 >= E4_3_prev else -1.0
        
        s += 1.0 if (d1 > _dz and d2 > _dz and d3 > _dz) else -1.0
        s += -1.0 if (d1 < -_dz and d2 < -_dz and d3 < -_dz) else 1.0
        
        s += 1.0 if (d1 > _dz and d2 > _dz and abs(d1) > abs(p[i-1]-p[i-2])) else -1.0
        s += -1.0 if (d1 < -_dz and d2 < -_dz and abs(d1) > abs(p[i-1]-p[i-2])) else 1.0
        
        score[i] = s / 31.0
        d1_out[i] = d1
        
    return score, d1_out

def run_simulation(df, index_name, ce_cols, pe_cols, params):
    _dz = params['_dz']
    vol_exp_thresh = params['vol_exp_thresh']
    vol_sig_mid = params['vol_sig_mid']
    noise_floor_param = params['noise_floor']
    conc_scale = params['conc_scale']
    idx_conf_ramp = params['idx_conf_ramp']
    
    idx_price = df[f'{index_name}_C'].values
    idx_atr = df[f'{index_name}_H'].values - df[f'{index_name}_L'].values
    # simple ATR approx for index
    
    idx_cum = f_cum_log_ret(idx_price)
    idx_score, _ = f_structural_score(idx_cum, _dz)
    idx_activity = np.abs(idx_score)
    idx_confidence = np.minimum(1.0, idx_activity / idx_conf_ramp)
    
    num_strikes = len(ce_cols)
    size = num_strikes
    n = len(df)
    
    final_score = np.zeros(n)
    
    ce_cum_all = [f_cum_log_ret(df[c].values) for c in ce_cols]
    pe_cum_all = [f_cum_log_ret(df[c].values) for c in pe_cols]
    
    ce_prices = [df[c].values for c in ce_cols]
    pe_prices = [df[c].values for c in pe_cols]
    
    ce_scores = []
    ce_vels = []
    pe_scores = []
    pe_vels = []
    
    for i in range(num_strikes):
        cs, cv = f_structural_score(ce_cum_all[i], _dz)
        ps, pv = f_structural_score(pe_cum_all[i], _dz)
        ce_scores.append(cs)
        ce_vels.append(cv)
        pe_scores.append(ps)
        pe_vels.append(pv)
        
    for i in range(10, n):
        idx_a = max(idx_atr[i], 1e-6)
        
        sum_dw = 0.0
        sum_w = 0.0
        n_vol_exp = 0
        
        hhi_sum = 0.0
        
        w_list = []
        for j in range(num_strikes):
            ce_chg = abs(ce_prices[j][i] - ce_prices[j][i-1])
            pe_chg = abs(pe_prices[j][i] - pe_prices[j][i-1])
            w = (ce_chg + pe_chg) / idx_a
            d = ce_scores[j][i] - pe_scores[j][i]
            
            sum_dw += d * w
            sum_w += w
            w_list.append(w)
            
            if ce_vels[j][i] > vol_exp_thresh and pe_vels[j][i] > vol_exp_thresh:
                n_vol_exp += 1
                
        raw = sum_dw / sum_w if sum_w > 0 else 0.0
        clamped = max(-1.0, min(1.0, raw / 2.0))
        
        vol_frac = n_vol_exp / size
        vol_penalty = 1.0 / (1.0 + np.exp(10.0 * (vol_frac - vol_sig_mid)))
        
        noise_floor = noise_floor_param * size
        noise_penalty = min(1.0, sum_w / max(noise_floor, 1e-6))
        
        hhi = 0.0
        if sum_w > 0:
            for w in w_list:
                share = w / sum_w
                hhi += share * share
                
        hhi_uniform = 1.0 / size
        conc_ratio = (hhi - hhi_uniform) / max(1.0 - hhi_uniform, 1e-6)
        conc_penalty = max(0.1, min(1.0, conc_ratio * conc_scale))
        
        penalty = vol_penalty * noise_penalty * conc_penalty * idx_confidence[i]
        final_score[i] = clamped * penalty
        
    return final_score

def evaluate_metrics(final_score, ground_truth):
    valid_idx = np.where(ground_truth != 0)[0]
    if len(valid_idx) == 0:
        hit_rate = 0
    else:
        hit_rate = np.mean(np.sign(final_score[valid_idx]) == np.sign(ground_truth[valid_idx]))
        
    flat_idx = np.where(ground_truth == 0)[0]
    if len(flat_idx) == 0:
        silence_acc = 0
    else:
        silence_acc = np.mean(np.abs(final_score[flat_idx]) < 0.05)
        
    strong_idx = np.where(np.abs(ground_truth) == 2)[0]
    mild_idx = np.where(np.abs(ground_truth) == 1)[0]
    
    if len(strong_idx) > 0 and len(mild_idx) > 0:
        mag_fidelity = np.mean(np.abs(final_score[strong_idx])) / max(np.mean(np.abs(final_score[mild_idx])), 1e-6)
    else:
        mag_fidelity = 0
        
    return hit_rate, silence_acc, mag_fidelity

if __name__ == '__main__':
    df_bn = load_pine_log('log csv/pine-logs-Simulation OHLC Matrix [Log CSV]_banknifty.csv')
    
    # Identify CE and PE close columns
    ce_cols = [c for c in df_bn.columns if 'CE' in c and c.endswith('_C')]
    pe_cols = [c for c in df_bn.columns if 'PE' in c and c.endswith('_C')]
    
    gt_bn = generate_ground_truth(df_bn, 'BANKNIFTY')
    
    # Default params
    params = {
        '_dz': 1e-6,
        'vol_exp_thresh': 1e-4,
        'vol_sig_mid': 0.4,
        'noise_floor': 0.02,
        'conc_scale': 3.0,
        'idx_conf_ramp': 0.3
    }
    
    base_score = run_simulation(df_bn, 'BANKNIFTY', ce_cols, pe_cols, params)
    base_hit, base_silence, base_mag = evaluate_metrics(base_score, gt_bn)
    print(f"Base metrics: Hit Rate: {base_hit:.2%}, Silence Acc: {base_silence:.2%}, Mag Fidelity: {base_mag:.2f}")
    
    # Sweep logic
    dz_range = [1e-8, 1e-6, 1e-4]
    vol_exp_range = [1e-5, 1e-4, 1e-3]
    vol_sig_mid_range = [0.2, 0.4, 0.6]
    noise_floor_range = [0.005, 0.02, 0.05]
    conc_scale_range = [1.0, 3.0, 5.0]
    idx_conf_ramp_range = [0.1, 0.3, 0.5]
    
    best_score = 0
    best_params = None
    best_metrics = None
    
    print("Starting sweep...")
    for dz, ve, vsm, nf, cs, icr in product(dz_range, vol_exp_range, vol_sig_mid_range, noise_floor_range, conc_scale_range, idx_conf_ramp_range):
        p = {
            '_dz': dz,
            'vol_exp_thresh': ve,
            'vol_sig_mid': vsm,
            'noise_floor': nf,
            'conc_scale': cs,
            'idx_conf_ramp': icr
        }
        
        score = run_simulation(df_bn, 'BANKNIFTY', ce_cols, pe_cols, p)
        hit, sil, mag = evaluate_metrics(score, gt_bn)
        
        # Custom score to maximize
        obj = hit * 100 + sil * 100 + min(mag, 3.0) * 10
        
        if obj > best_score:
            best_score = obj
            best_params = p
            best_metrics = (hit, sil, mag)
    
    print("\nBest Parameters:")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
        
    print("\nBest Metrics:")
    print(f"  Hit Rate: {best_metrics[0]:.2%}")
    print(f"  Silence Accuracy: {best_metrics[1]:.2%}")
    print(f"  Magnitude Fidelity: {best_metrics[2]:.2f}")
