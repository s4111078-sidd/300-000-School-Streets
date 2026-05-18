"""
ML Model — Predict Healthy Streets Indicator Scores
Trains a Ridge regression on ml_school_features.csv to predict
HS1–HS10 indicator scores from open spatial/environmental/crash data.

Purpose: demonstrate that HS scores can be estimated from freely
available OSM, AQI, crime, and crash data without field surveys.

Evaluation: Leave-One-Out CV (LOO-CV) — appropriate for 3 schools.
            Train on 2 schools, predict the left-out school.

Run:    python ml_model.py
Output: outputs/chart_hs_correlation.png   — feature × indicator heatmap
        outputs/chart_hs_prediction.png    — actual vs predicted (LOO-CV)
        outputs/chart_feature_importance.png — top features per indicator
        outputs/ml_predictions.csv         — LOO-CV predictions table
        outputs/hs_predictor.pkl           — model trained on all 3 schools
"""

import os
import pickle
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

from sklearn.linear_model  import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline      import Pipeline
from sklearn.multioutput   import MultiOutputRegressor
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics       import mean_absolute_error

IN_CSV  = os.path.join('outputs', 'ml_school_features.csv')
OUT_DIR = 'outputs'
os.makedirs(OUT_DIR, exist_ok=True)

NAVY  = '#0A2342'
TEAL  = '#1A8FC1'
AMBER = '#E8A838'
RED   = '#C0392B'
GREEN = '#27AE60'
GREY  = '#888888'
WHITE = '#FFFFFF'

HS_TARGETS = ['HS1','HS2','HS3','HS4','HS5','HS6','HS7','HS8','HS9','HS10']
HS_LABELS  = [
    'HS1\nPedestrians',
    'HS2\nCrossings',
    'HS3\nShade/Shelter',
    'HS4\nRest Places',
    'HS5\nNot Noisy',
    'HS6\nActive Travel',
    'HS7\nFeel Safe',
    'HS8\nThings To Do',
    'HS9\nFeel Relaxed',
    'HS10\nClean Air',
]

# colour each feature group to match its HS indicator
FEAT_GROUP_COLOUR = {
    'footpath':    GREEN,   # HS1
    'crossings':   TEAL,    # HS2
    'signals':     TEAL,
    'crossing_density': TEAL,
    'tree':        '#2ECC71',  # HS3
    'shelter':     '#2ECC71',
    'green_pct':   '#2ECC71',
    'bench':       AMBER,   # HS4
    'park':        AMBER,
    'avg_speed':   RED,     # HS5/9
    'arterial':    RED,
    'high_speed':  RED,
    'road_count':  RED,
    'cycle':       '#3498DB',  # HS6
    'protected':   '#3498DB',
    'pt_stops':    '#3498DB',
    'amenity':     '#9B59B6',  # HS8
    'cafe':        '#9B59B6',
    'walk_length': GREY,
    'crime':       '#E74C3C',  # HS7
    'aqi':         '#1ABC9C',  # HS10
    'crash':       '#E67E22',
    'serious':     '#E67E22',
    'school_hours':'#E67E22',
    'avg_speed_zone': '#E67E22',
}

def feat_colour(name):
    for key, col in FEAT_GROUP_COLOUR.items():
        if key in name:
            return col
    return GREY


print('\n' + '='*60)
print('  ML Model — HS Score Prediction')
print('='*60)

# ── 1. Load data ───────────────────────────────────────────────────────────────
print(f'\nLoading {IN_CSV}...')
df = pd.read_csv(IN_CSV)
print(f'  {len(df)} schools  |  {len(df.columns)} columns')

schools = df['school'].tolist()
X = df[df.columns.difference(['school'] + HS_TARGETS + ['HS_overall'])].copy()
X = X[sorted(X.columns)]   # deterministic column order
Y = df[HS_TARGETS].copy()

print(f'  Feature matrix X: {X.shape}')
print(f'  Target matrix  Y: {Y.shape}')

# ── 2. LOO-CV predictions ──────────────────────────────────────────────────────
print('\n[LOO-CV] Leave-One-Out cross-validation (n=3)...')

loo    = LeaveOneOut()
preds  = np.full_like(Y.values, np.nan, dtype=float)

for train_idx, test_idx in loo.split(X):
    X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
    y_tr        = Y.iloc[train_idx]

    pipe = Pipeline([
        ('scaler', StandardScaler()),
        ('model',  MultiOutputRegressor(Ridge(alpha=1.0))),
    ])
    pipe.fit(X_tr, y_tr)
    preds[test_idx] = np.clip(pipe.predict(X_te), 0, 10)

pred_df = pd.DataFrame(preds, columns=[f'{c}_pred' for c in HS_TARGETS])
pred_df.insert(0, 'school', schools)
for c in HS_TARGETS:
    pred_df[f'{c}_actual'] = Y[c].values

# per-indicator MAE
mae = {c: mean_absolute_error(Y[c], pred_df[f'{c}_pred']) for c in HS_TARGETS}
print(f'\n  LOO-CV MAE per indicator:')
for c, v in mae.items():
    bar = '█' * int(round(v))
    print(f'    {c}   {v:.2f}  {bar}')

pred_out = os.path.join(OUT_DIR, 'ml_predictions.csv')
pred_df.to_csv(pred_out, index=False)
print(f'\n  Predictions saved -> {pred_out}')

# ── 3. Full model (train on all 3 schools) ─────────────────────────────────────
full_pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('model',  MultiOutputRegressor(Ridge(alpha=1.0))),
])
full_pipe.fit(X, Y)

# extract ridge coefficients per target
scaler = full_pipe.named_steps['scaler']
estimators = full_pipe.named_steps['model'].estimators_
coef_matrix = np.vstack([e.coef_ for e in estimators])   # (10, n_features)
coef_df = pd.DataFrame(coef_matrix, index=HS_TARGETS, columns=X.columns)

# ── 4. Feature-Indicator Correlation Heatmap ──────────────────────────────────
print('\n[Chart 1/3] Feature-indicator Pearson correlation heatmap...')

feat_target_corr = pd.DataFrame(index=X.columns, columns=HS_TARGETS, dtype=float)
for f in X.columns:
    for t in HS_TARGETS:
        if X[f].std() == 0 or Y[t].std() == 0:
            feat_target_corr.loc[f, t] = 0.0
        else:
            feat_target_corr.loc[f, t] = np.corrcoef(X[f], Y[t])[0, 1]

feat_target_corr = feat_target_corr.astype(float)

fig, ax = plt.subplots(figsize=(13, 9))
fig.patch.set_facecolor(WHITE)

sns.heatmap(
    feat_target_corr,
    ax=ax,
    cmap='RdYlGn',
    vmin=-1, vmax=1,
    center=0,
    annot=True,
    fmt='.2f',
    annot_kws={'size': 7},
    linewidths=0.4,
    linecolor='#EEEEEE',
    cbar_kws={'label': 'Pearson r', 'shrink': 0.7},
)
ax.set_title(
    'Open-Data Feature vs Healthy Streets Indicator — Pearson Correlation\n'
    '(n=3 schools; values show direction of alignment between feature and HS score)',
    fontsize=11, fontweight='bold', pad=12,
)
ax.set_xlabel('Healthy Streets Indicator', fontsize=10, labelpad=8)
ax.set_ylabel('Open-data Feature', fontsize=10, labelpad=8)
ax.set_xticklabels(HS_LABELS, fontsize=8, rotation=0)
ax.set_yticklabels(ax.get_yticklabels(), fontsize=7, rotation=0)

# colour y-tick labels by feature group
for label in ax.get_yticklabels():
    label.set_color(feat_colour(label.get_text()))

plt.figtext(0.99, 0.01, '300,000 Streets  |  Regen Melbourne × RMIT University',
            ha='right', fontsize=7, color=GREY)
plt.tight_layout()
corr_path = os.path.join(OUT_DIR, 'chart_hs_correlation.png')
plt.savefig(corr_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'  Saved -> {corr_path}')

# ── 5. Actual vs Predicted — LOO-CV bar chart ──────────────────────────────────
print('\n[Chart 2/3] Actual vs predicted HS scores (LOO-CV)...')

fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
fig.patch.set_facecolor(WHITE)
fig.suptitle(
    'Predicted vs Actual Healthy Streets Scores — LOO-CV\n'
    '(Each school predicted by model trained on the other two)',
    fontsize=12, fontweight='bold', y=1.02,
)

x_pos = np.arange(len(HS_TARGETS))
w = 0.38

for ax, school in zip(axes, schools):
    row = pred_df[pred_df['school'] == school].iloc[0]
    actuals = [row[f'{c}_actual'] for c in HS_TARGETS]
    predictd = [row[f'{c}_pred']   for c in HS_TARGETS]

    b1 = ax.bar(x_pos - w/2, actuals,  w, label='Actual',    color=NAVY,  alpha=0.85, edgecolor='white')
    b2 = ax.bar(x_pos + w/2, predictd, w, label='Predicted', color=TEAL,  alpha=0.85, edgecolor='white')

    for bar, val in zip(b1, actuals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
                f'{val:.1f}', ha='center', va='bottom', fontsize=6.5, color=NAVY)
    for bar, val in zip(b2, predictd):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
                f'{val:.1f}', ha='center', va='bottom', fontsize=6.5, color=TEAL)

    school_mae = np.mean([abs(a - p) for a, p in zip(actuals, predictd)])
    ax.set_title(f'{school}\nMean MAE: {school_mae:.2f}', fontsize=10, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels([c for c in HS_TARGETS], fontsize=8)
    ax.set_ylim(0, 12)
    ax.set_ylabel('Score (0–10)', fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, color='#EEEEEE', linewidth=0.6)
    ax.set_axisbelow(True)

handles = [mpatches.Patch(color=NAVY, label='Actual'),
           mpatches.Patch(color=TEAL, label='Predicted (LOO-CV)')]
fig.legend(handles=handles, loc='lower center', ncol=2, fontsize=9,
           framealpha=0.9, bbox_to_anchor=(0.5, -0.04))

plt.figtext(0.99, 0.01, '300,000 Streets  |  Regen Melbourne × RMIT University',
            ha='right', fontsize=7, color=GREY)
plt.tight_layout()
pred_path = os.path.join(OUT_DIR, 'chart_hs_prediction.png')
plt.savefig(pred_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'  Saved -> {pred_path}')

# ── 6. Top features per indicator (Ridge coefficients) ────────────────────────
print('\n[Chart 3/3] Top features per HS indicator (Ridge coefficients)...')

fig, axes = plt.subplots(2, 5, figsize=(18, 9))
fig.patch.set_facecolor(WHITE)
fig.suptitle(
    'Top Open-Data Predictors per Healthy Streets Indicator\n'
    '(Ridge regression coefficients — model trained on all 3 schools)',
    fontsize=12, fontweight='bold', y=1.01,
)

for ax, indicator in zip(axes.flatten(), HS_TARGETS):
    coefs = coef_df.loc[indicator].sort_values(key=abs, ascending=False).head(8)
    colours = [GREEN if v >= 0 else RED for v in coefs.values]
    ax.barh(coefs.index[::-1], coefs.values[::-1], color=colours[::-1], edgecolor='white', height=0.6)
    ax.axvline(0, color='black', linewidth=0.6)
    ax.set_title(indicator, fontsize=10, fontweight='bold')
    ax.set_xlabel('Coefficient', fontsize=7)
    ax.tick_params(axis='y', labelsize=7)
    ax.tick_params(axis='x', labelsize=7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

pos_patch = mpatches.Patch(color=GREEN, label='Positive (feature ↑ → score ↑)')
neg_patch = mpatches.Patch(color=RED,   label='Negative (feature ↑ → score ↓)')
fig.legend(handles=[pos_patch, neg_patch], loc='lower center', ncol=2,
           fontsize=9, framealpha=0.9, bbox_to_anchor=(0.5, -0.03))

plt.figtext(0.99, 0.01, '300,000 Streets  |  Regen Melbourne × RMIT University',
            ha='right', fontsize=7, color=GREY)
plt.tight_layout()
fi_path = os.path.join(OUT_DIR, 'chart_feature_importance.png')
plt.savefig(fi_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'  Saved -> {fi_path}')

# ── 7. Save model ──────────────────────────────────────────────────────────────
pkl_path = os.path.join(OUT_DIR, 'hs_predictor.pkl')
with open(pkl_path, 'wb') as f:
    pickle.dump({
        'model':    full_pipe,
        'features': X.columns.tolist(),
        'targets':  HS_TARGETS,
        'schools':  schools,
    }, f)
print(f'\n  Model saved -> {pkl_path}')

# ── 8. Summary ─────────────────────────────────────────────────────────────────
mean_mae = np.mean(list(mae.values()))
best_ind  = min(mae, key=mae.get)
worst_ind = max(mae, key=mae.get)

print(f'\n{"="*60}')
print(f'  RESULTS SUMMARY')
print(f'{"="*60}')
print(f'  Model:        Ridge regression (multi-output)')
print(f'  Evaluation:   LOO-CV  (n=3 schools)')
print(f'  Features:     {X.shape[1]}  (spatial + environmental + crash stats)')
print(f'  Targets:      10  (HS1–HS10)')
print(f'\n  Mean LOO-CV MAE across all indicators: {mean_mae:.2f}')
print(f'  Best predicted:  {best_ind}  (MAE {mae[best_ind]:.2f})')
print(f'  Hardest to predict: {worst_ind}  (MAE {mae[worst_ind]:.2f})')
print(f'\n  Note: n=3 schools — results are illustrative.')
print(f'  Adding more schools will improve generalisability.')
print(f'\n  Outputs:')
print(f'    {corr_path}')
print(f'    {pred_path}')
print(f'    {fi_path}')
print(f'    {pred_out}')
print(f'    {pkl_path}')
print(f'{"="*60}')
print(f'\n  Prediction table:')
summary_cols = ['school'] + [f'{c}_actual' for c in HS_TARGETS]
print(pred_df[summary_cols].rename(columns={f'{c}_actual': c for c in HS_TARGETS}).to_string(index=False))
print()
pred_cols = ['school'] + [f'{c}_pred' for c in HS_TARGETS]
print(pred_df[pred_cols].rename(columns={f'{c}_pred': f'{c}ₚ' for c in HS_TARGETS}).to_string(index=False))
