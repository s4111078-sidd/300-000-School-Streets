"""
ML Model — School Streets Crash Risk Classification
Trains Random Forest and XGBoost classifiers on ml_features.csv to predict
serious or fatal crash risk near school gates.

Target: serious_or_fatal  (1 = fatal or serious injury, 0 = other injury)
Positive rate: ~43%

Run:    python ml_model.py
Output: outputs/chart_feature_importance.png
        outputs/crash_risk_model.pkl   (best model by ROC-AUC)
"""

import os
import pickle
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    classification_report, roc_auc_score, confusion_matrix, ConfusionMatrixDisplay
)
from sklearn.pipeline import Pipeline

IN_CSV  = os.path.join('outputs', 'ml_features.csv')
OUT_DIR = 'outputs'
OUT_FIG = os.path.join(OUT_DIR, 'chart_feature_importance.png')
OUT_PKL = os.path.join(OUT_DIR, 'crash_risk_model.pkl')

# ── 1. Load ────────────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('  ML Model — Crash Risk Classification')
print('='*60)
print(f'\nLoading {IN_CSV}...')

df = pd.read_csv(IN_CSV, low_memory=False)
print(f'  {len(df):,} rows  |  {len(df.columns)} columns')

# ── 2. Prepare features and target ────────────────────────────────────────────
DROP_COLS = ['ACCIDENT_NO', 'nearest_school', 'serious_or_fatal']
TARGET    = 'serious_or_fatal'

y = df[TARGET].astype(int)
X = df.drop(columns=[c for c in DROP_COLS if c in df.columns])

# Drop columns that are entirely NaN — imputer can't fill these and RF will skip them
all_nan = X.columns[X.isna().all()].tolist()
if all_nan:
    print(f'  Dropping all-NaN columns: {all_nan}')
    X = X.drop(columns=all_nan)

print(f'  Target balance: {y.sum():,} serious/fatal ({y.mean()*100:.1f}%)')
print(f'  Features: {X.shape[1]}')

# ── 3. Train / test split (stratified) ────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f'\n  Train: {len(X_train):,}  |  Test: {len(X_test):,}')

# ── 4. Define models ───────────────────────────────────────────────────────────
imputer = SimpleImputer(strategy='median')

rf = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('model',   RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
    )),
])

models = {'Random Forest': rf}

# ── 5. Train and evaluate ──────────────────────────────────────────────────────
results = {}
print('\n' + '-'*60)

for name, pipe in models.items():
    print(f'\n  Training {name}...')
    pipe.fit(X_train, y_train)

    y_pred  = pipe.predict(X_test)
    y_proba = pipe.predict_proba(X_test)[:, 1]
    auc     = roc_auc_score(y_test, y_proba)

    print(f'\n  {name} — ROC-AUC: {auc:.4f}')
    print(f'\n{classification_report(y_test, y_pred, target_names=["Other injury", "Serious/Fatal"])}')

    cv_auc = cross_val_score(pipe, X_train, y_train, cv=StratifiedKFold(5),
                             scoring='roc_auc', n_jobs=-1)
    print(f'  5-fold CV AUC: {cv_auc.mean():.4f} ± {cv_auc.std():.4f}')

    results[name] = {
        'pipe': pipe, 'auc': auc, 'y_pred': y_pred, 'y_proba': y_proba,
    }

# ── 6. Pick best model ─────────────────────────────────────────────────────────
best_name = max(results, key=lambda n: results[n]['auc'])
best      = results[best_name]
print(f'\n  Best model: {best_name}  (AUC {best["auc"]:.4f})')

# ── 7. Confusion matrices ──────────────────────────────────────────────────────
fig, axes = plt.subplots(1, len(results), figsize=(6 * len(results), 5))
if len(results) == 1:
    axes = [axes]
fig.patch.set_facecolor('white')
fig.suptitle('Confusion Matrix — Test Set', fontsize=14, fontweight='bold')

for ax, (name, res) in zip(axes, results.items()):
    cm = confusion_matrix(y_test, res['y_pred'])
    disp = ConfusionMatrixDisplay(cm, display_labels=['Other', 'Serious/Fatal'])
    disp.plot(ax=ax, colorbar=False, cmap='Blues')
    ax.set_title(f'{name}\nAUC = {res["auc"]:.4f}', fontsize=11, fontweight='bold')

plt.tight_layout()
cm_path = os.path.join(OUT_DIR, 'chart_confusion_matrix.png')
plt.savefig(cm_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'\n  Saved -> {cm_path}')

# ── 8. Feature importance chart ────────────────────────────────────────────────
print('\n  Building feature importance chart...')

fig, axes = plt.subplots(1, len(results), figsize=(9 * len(results), 10))
if len(results) == 1:
    axes = [axes]
fig.patch.set_facecolor('white')
fig.suptitle('Top 20 Feature Importances', fontsize=14, fontweight='bold', y=1.01)

for ax, (name, res) in zip(axes, results.items()):
    model     = res['pipe'].named_steps['model']
    imp       = model.feature_importances_
    feat_names = X.columns.tolist()

    fi = pd.Series(imp, index=feat_names).sort_values(ascending=False).head(20)

    colours = []
    for f in fi.index:
        if any(k in f for k in ('cycle', 'cys')):
            colours.append('#1A8FC1')   # blue — cycling
        elif any(k in f for k in ('walk', 'foot', 'crossing', 'signal')):
            colours.append('#27AE60')   # green — pedestrian
        elif any(k in f for k in ('speed', 'arterial', 'road', 'high_speed')):
            colours.append('#C0392B')   # red — road danger
        elif any(k in f for k in ('hour', 'day', 'month', 'weekend', 'school_hours')):
            colours.append('#8E44AD')   # purple — time
        else:
            colours.append('#555555')   # grey — other

    ax.barh(fi.index[::-1], fi.values[::-1], color=colours[::-1], edgecolor='white')
    ax.set_title(name, fontsize=12, fontweight='bold')
    ax.set_xlabel('Feature Importance', fontsize=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.xaxis.grid(True, color='#DDDDDD', linewidth=0.6)
    ax.set_axisbelow(True)

legend_els = [
    mpatches.Patch(color='#C0392B', label='Road / speed'),
    mpatches.Patch(color='#27AE60', label='Pedestrian / crossing'),
    mpatches.Patch(color='#1A8FC1', label='Cycling'),
    mpatches.Patch(color='#8E44AD', label='Time'),
    mpatches.Patch(color='#555555', label='Other'),
]
fig.legend(handles=legend_els, loc='lower center', ncol=5,
           fontsize=9, framealpha=0.8, bbox_to_anchor=(0.5, -0.03))
plt.figtext(0.99, 0.01, '300,000 Streets  |  Regen Melbourne x RMIT University',
            ha='right', fontsize=8, color='#888888')
plt.tight_layout()
plt.savefig(OUT_FIG, dpi=150, bbox_inches='tight')
plt.close()
print(f'  Saved -> {OUT_FIG}')

# ── 9. Save best model ─────────────────────────────────────────────────────────
with open(OUT_PKL, 'wb') as f:
    pickle.dump({'model': best['pipe'], 'features': X.columns.tolist(),
                 'model_name': best_name}, f)
print(f'  Saved -> {OUT_PKL}  ({best_name})')

# ── 10. Summary ────────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('  RESULTS SUMMARY')
print('='*60)
for name, res in results.items():
    print(f'  {name:<20}  ROC-AUC: {res["auc"]:.4f}')
print(f'\n  Best model : {best_name}')
print(f'  Saved to   : {OUT_PKL}')
print(f'\n  Outputs:')
print(f'    {OUT_FIG}')
print(f'    {cm_path}')
print(f'    {OUT_PKL}')
print('='*60)
