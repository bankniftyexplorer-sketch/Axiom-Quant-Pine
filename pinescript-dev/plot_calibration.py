import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from calibrate_physics import load_pine_log, generate_ground_truth, run_simulation

df_bn = load_pine_log('log csv/pine-logs-Simulation OHLC Matrix [Log CSV]_banknifty.csv')
ce_cols = [c for c in df_bn.columns if 'CE' in c and c.endswith('_C')]
pe_cols = [c for c in df_bn.columns if 'PE' in c and c.endswith('_C')]
gt_bn = generate_ground_truth(df_bn, 'BANKNIFTY')

best_params = {
    '_dz': 1e-08,
    'vol_exp_thresh': 1e-05,
    'vol_sig_mid': 0.2,
    'noise_floor': 0.005,
    'conc_scale': 1.0,
    'idx_conf_ramp': 0.5
}

score = run_simulation(df_bn, 'BANKNIFTY', ce_cols, pe_cols, best_params)

# Spearman correlation
spearman_corr, _ = spearmanr(score, gt_bn)

valid_idx = np.where(gt_bn != 0)[0]
hit_rate = np.mean(np.sign(score[valid_idx]) == np.sign(gt_bn[valid_idx]))

# False positive rate (score > 0.3 when truth is 0)
flat_idx = np.where(gt_bn == 0)[0]
fpr = np.mean(np.abs(score[flat_idx]) > 0.3)

print(f"Spearman: {spearman_corr:.3f}")
print(f"Hit Rate: {hit_rate:.2%}")
print(f"False Positive Rate: {fpr:.2%}")

plt.figure(figsize=(15, 6))
plt.plot(df_bn.index, score, label='Comparator Score', color='blue', linewidth=1.5)
plt.scatter(df_bn.index[gt_bn == 2], [1.1]*np.sum(gt_bn == 2), color='green', marker='^', label='Truth: +2')
plt.scatter(df_bn.index[gt_bn == 1], [1.05]*np.sum(gt_bn == 1), color='lightgreen', marker='^', label='Truth: +1')
plt.scatter(df_bn.index[gt_bn == -1], [-1.05]*np.sum(gt_bn == -1), color='salmon', marker='v', label='Truth: -1')
plt.scatter(df_bn.index[gt_bn == -2], [-1.1]*np.sum(gt_bn == -2), color='red', marker='v', label='Truth: -2')
plt.axhline(0, color='black', linewidth=1)
plt.axhline(0.05, color='gray', linestyle='--', alpha=0.5)
plt.axhline(-0.05, color='gray', linestyle='--', alpha=0.5)
plt.ylim(-1.2, 1.2)
plt.title('ComparatorScore Calibration vs Ground Truth (BANKNIFTY)')
plt.legend()
plt.tight_layout()
plt.savefig('/home/km/.gemini/antigravity/brain/0f0adc3c-3ca8-4f56-8bfc-ce94c18c7847/artifacts/calibration_plot.png')
