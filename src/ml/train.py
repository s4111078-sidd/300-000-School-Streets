"""
ML Model — School Streets Crash Risk Classification.

Trains a Random Forest classifier on ml_features.csv to predict
serious or fatal crash risk near school gates.

Target:       serious_or_fatal  (1 = fatal or serious injury, 0 = other)
Positive rate: ~43%

Outputs:
  outputs/chart_feature_importance.png
  outputs/chart_confusion_matrix.png
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

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    classification_report, roc_auc_score, confusion_matrix, ConfusionMatrixDisplay
)
from sklearn.pipeline import Pipeline


def train_model(
    in_csv: str = None,
    out_dir: str = None,
) -> dict:
    """
    Train crash-risk classifier on ml_features.csv.

    Args:
        in_csv:  path to ml_features.csv  (default: outputs/ml_features.csv)
        out_dir: directory for output files (default: outputs)

    Returns:
        dict with keys: model_name, auc, model_path, fig_importance, fig_confusion
    """
    if in_csv   is None: in_csv   = os.path.join('outputs', 'ml_features.csv')
    if out_dir  is None: out_dir  = 'outputs'

    out_fig = os.path.join(out_dir, 'chart_feature_importance.png')
    out_pkl = os.path.join(out_dir, 'crash_risk_model.pkl')

    print('\n' + '='*60)
    print('  ML Model — Crash Risk Classification')
    print('='*60)
    print(f'\nLoading {in_csv}...')

    df = pd.read_csv(in_csv, low_memory=False)
    print(f'  {len(df):,} rows  |  {len(df.columns)} columns')

    DROP_COLS = ['ACCIDENT_NO', 'nearest_school', 'serious_or_fatal']
    TARGET    = 'serious_or_fatal'

    y = df[TARGET].astype(int)
    X = df.drop(columns=[c for c in DROP_COLS if c in df.columns])

    all_nan = X.columns[X.isna().all()].tolist()
    if all_nan:
        print(f'  Dropping all-NaN columns: {all_nan}')
        X = X.drop(columns=all_nan)

    print(f'  Target balance: {y.sum():,} serious/fatal ({y.mean()*100:.1f}%)')
    print(f'  Features: {X.shape[1]}')

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f'\n  Train: {len(X_train):,}  |  Test: {len(X_test):,}')

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

    best_name = max(results, key=lambda n: results[n]['auc'])
    best      = results[best_name]
    print(f'\n  Best model: {best_name}  (AUC {best["auc"]:.4f})')

    # ── Confusion matrices ─────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, len(results), figsize=(6 * len(results), 5))
    if len(results) == 1:
        axes = [axes]
    fig.patch.set_facecolor('white')
    fig.suptitle('Confusion Matrix — Test Set', fontsize=14, fontweight='bold')

    for ax, (name, res) in zip(axes, results.items()):
        cm   = confusion_matrix(y_test, res['y_pred'])
        disp = ConfusionMatrixDisplay(cm, display_labels=['Other', 'Serious/Fatal'])
        disp.plot(ax=ax, colorbar=False, cmap='Blues')
        ax.set_title(f'{name}\nAUC = {res["auc"]:.4f}', fontsize=11, fontweight='bold')

    plt.tight_layout()
    cm_path = os.path.join(out_dir, 'chart_confusion_matrix.png')
    plt.savefig(cm_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'\n  Saved -> {cm_path}')

    # ── Feature importance chart ───────────────────────────────────────────────
    print('\n  Building feature importance chart...')

    fig, axes = plt.subplots(1, len(results), figsize=(9 * len(results), 10))
    if len(results) == 1:
        axes = [axes]
    fig.patch.set_facecolor('white')
    fig.suptitle('Top 20 Feature Importances', fontsize=14, fontweight='bold', y=1.01)

    for ax, (name, res) in zip(axes, results.items()):
        model      = res['pipe'].named_steps['model']
        imp        = model.feature_importances_
        feat_names = X.columns.tolist()

        fi = pd.Series(imp, index=feat_names).sort_values(ascending=False).head(20)

        colours = []
        for f in fi.index:
            if any(k in f for k in ('cycle', 'cys')):
                colours.append('#1A8FC1')
            elif any(k in f for k in ('walk', 'foot', 'crossing', 'signal')):
                colours.append('#27AE60')
            elif any(k in f for k in ('speed', 'arterial', 'road', 'high_speed')):
                colours.append('#C0392B')
            elif any(k in f for k in ('hour', 'day', 'month', 'weekend', 'school_hours')):
                colours.append('#8E44AD')
            else:
                colours.append('#555555')

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
    plt.savefig(out_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  Saved -> {out_fig}')

    # ── Save best model ────────────────────────────────────────────────────────
    with open(out_pkl, 'wb') as f:
        pickle.dump({'model': best['pipe'], 'features': X.columns.tolist(),
                     'model_name': best_name}, f)
    print(f'  Saved -> {out_pkl}  ({best_name})')

    print('\n' + '='*60)
    print('  RESULTS SUMMARY')
    print('='*60)
    for name, res in results.items():
        print(f'  {name:<20}  ROC-AUC: {res["auc"]:.4f}')
    print(f'\n  Best model : {best_name}')
    print(f'  Saved to   : {out_pkl}')
    print(f'\n  Outputs:')
    print(f'    {out_fig}')
    print(f'    {cm_path}')
    print(f'    {out_pkl}')
    print('='*60)

    return {
        'model_name':      best_name,
        'auc':             best['auc'],
        'model_path':      out_pkl,
        'fig_importance':  out_fig,
        'fig_confusion':   cm_path,
    }


if __name__ == '__main__':
    train_model()
