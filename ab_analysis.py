import pandas as pd
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns
import hashlib
import time
import os

# Set random seed and plotting styles
np.random.seed(42)
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    'font.size': 12,
    'axes.labelsize': 14,
    'axes.titlesize': 16,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'figure.titlesize': 18
})

file_path = "/Users/jhanvimattil/Downloads/archive (1)/2019-Oct.csv"
artifacts_dir = "/Users/jhanvimattil/.gemini/antigravity/brain/d68c7ce6-ce59-4960-b0c5-eba592a8dd38/artifacts"
os.makedirs(artifacts_dir, exist_ok=True)

print("Starting A/B test simulation and analysis...")
start_time = time.time()

# 1. Load Data (first 15M rows)
print("Loading first 15,000,000 rows from 2019-Oct.csv...")
df = pd.read_csv(file_path, nrows=15000000, usecols=['user_id', 'event_type', 'price'])
print(f"Loaded in {time.time() - start_time:.2f} seconds.")

# Clean data
df = df.dropna(subset=['user_id', 'event_type'])

# 2. Extract baseline price metrics for simulation
print("Calculating baseline price statistics...")
median_price = df[df['event_type'] == 'view']['price'].median()
if np.isnan(median_price):
    median_price = 100.0 # fallback

# Pre-calculate boolean indicators and helper columns for vectorized groupby
df['is_view'] = (df['event_type'] == 'view').astype(int)
df['is_cart'] = (df['event_type'] == 'cart').astype(int)
df['is_purchase'] = (df['event_type'] == 'purchase').astype(int)
df['purchase_revenue'] = np.where(df['event_type'] == 'purchase', df['price'], 0.0)
df['view_price'] = np.where(df['event_type'] == 'view', df['price'], np.nan)

# Compute user-level metrics in baseline data (vectorized groupby)
print("Aggregating baseline metrics by user (vectorized)...")
user_stats = df.groupby('user_id').agg(
    total_views=('is_view', 'sum'),
    total_carts=('is_cart', 'sum'),
    total_purchases=('is_purchase', 'sum'),
    original_revenue=('purchase_revenue', 'sum'),
    mean_view_price=('view_price', 'mean')
).reset_index()

# Replace missing mean view price with median price
user_stats['mean_view_price'] = user_stats['mean_view_price'].fillna(median_price)

print(f"Aggregated data for {len(user_stats):,} unique users.")

# 3. Assign Users to Groups using MD5
print("Assigning users to A/B groups...")
# Vectorized group assignment using MD5 hash of user_id
def get_group_vectorized(ids):
    groups = []
    for uid in ids:
        hash_val = int(hashlib.md5(str(uid).encode()).hexdigest(), 16)
        groups.append('Variant A (Discount)' if hash_val % 2 == 0 else 'Variant B (Premium)')
    return np.array(groups)

user_stats['group'] = get_group_vectorized(user_stats['user_id'].values)
print(user_stats['group'].value_counts())

# 4. Simulate Treatment Effects
print("Simulating banner treatment effects...")
n_users = len(user_stats)
rand_vals = np.random.rand(n_users)

group_mask_A = user_stats['group'] == 'Variant A (Discount)'
group_mask_B = user_stats['group'] == 'Variant B (Premium)'

# Set up conversion columns
user_stats['sim_purchases'] = user_stats['total_purchases']
user_stats['sim_revenue'] = user_stats['original_revenue']

# Variant A conversions for non-buyers with views
conv_mask_A = group_mask_A & (user_stats['total_purchases'] == 0) & (user_stats['total_views'] > 0) & (rand_vals < 0.022)
user_stats.loc[conv_mask_A, 'sim_purchases'] = 1
user_stats.loc[conv_mask_A, 'sim_revenue'] = user_stats.loc[conv_mask_A, 'mean_view_price']

# Apply discount to Variant A revenue
user_stats.loc[group_mask_A, 'sim_revenue'] = user_stats.loc[group_mask_A, 'sim_revenue'] * 0.85

# Variant B conversions for non-buyers with views
conv_mask_B = group_mask_B & (user_stats['total_purchases'] == 0) & (user_stats['total_views'] > 0) & (rand_vals < 0.008)
user_stats.loc[conv_mask_B, 'sim_purchases'] = 1
user_stats.loc[conv_mask_B, 'sim_revenue'] = user_stats.loc[conv_mask_B, 'mean_view_price']

# Apply premium to Variant B revenue
user_stats.loc[group_mask_B, 'sim_revenue'] = user_stats.loc[group_mask_B, 'sim_revenue'] * 1.05

# Final buyer flag
user_stats['is_buyer'] = user_stats['sim_purchases'] > 0

# 5. Run Statistical Analysis
print("Calculating A/B test statistics...")

# Group splits
df_A = user_stats[group_mask_A]
df_B = user_stats[group_mask_B]

n_A = len(df_A)
n_B = len(df_B)

buyers_A = df_A['is_buyer'].sum()
buyers_B = df_B['is_buyer'].sum()

cr_A = buyers_A / n_A
cr_B = buyers_B / n_B

rev_A = df_A['sim_revenue'].sum()
rev_B = df_B['sim_revenue'].sum()

rpv_A = df_A['sim_revenue'].mean()
rpv_B = df_B['sim_revenue'].mean()
rpv_std_A = df_A['sim_revenue'].std()
rpv_std_B = df_B['sim_revenue'].std()

purchases_A = df_A['sim_purchases'].sum()
purchases_B = df_B['sim_purchases'].sum()

aov_A = rev_A / purchases_A if purchases_A > 0 else 0
aov_B = rev_B / purchases_B if purchases_B > 0 else 0

# Standard errors and confidence intervals for CR
se_cr_A = np.sqrt(cr_A * (1 - cr_A) / n_A)
se_cr_B = np.sqrt(cr_B * (1 - cr_B) / n_B)
ci_cr_A = (cr_A - 1.96 * se_cr_A, cr_A + 1.96 * se_cr_A)
ci_cr_B = (cr_B - 1.96 * se_cr_B, cr_B + 1.96 * se_cr_B)

# Z-test for Conversion Rate
p_pooled = (buyers_A + buyers_B) / (n_A + n_B)
se_pooled = np.sqrt(p_pooled * (1 - p_pooled) * (1/n_A + 1/n_B))
z_stat = (cr_A - cr_B) / se_pooled
cr_p_value = stats.norm.sf(abs(z_stat)) * 2

# Standard errors and confidence intervals for RPV
se_rpv_A = rpv_std_A / np.sqrt(n_A)
se_rpv_B = rpv_std_B / np.sqrt(n_B)
ci_rpv_A = (rpv_A - 1.96 * se_rpv_A, rpv_A + 1.96 * se_rpv_A)
ci_rpv_B = (rpv_B - 1.96 * se_rpv_B, rpv_B + 1.96 * se_rpv_B)

# T-test for RPV (Welch's t-test)
rpv_t_stat, rpv_p_value = stats.ttest_ind(df_A['sim_revenue'], df_B['sim_revenue'], equal_var=False)

# AOV statistics (for buyers only)
buyers_A_data = df_A[df_A['is_buyer']]
buyers_B_data = df_B[df_B['is_buyer']]

user_aov_A = buyers_A_data['sim_revenue'] / buyers_A_data['sim_purchases']
user_aov_B = buyers_B_data['sim_revenue'] / buyers_B_data['sim_purchases']

mean_user_aov_A = user_aov_A.mean()
mean_user_aov_B = user_aov_B.mean()
std_user_aov_A = user_aov_A.std()
std_user_aov_B = user_aov_B.std()

se_aov_A = std_user_aov_A / np.sqrt(len(user_aov_A))
se_aov_B = std_user_aov_B / np.sqrt(len(user_aov_B))
ci_aov_A = (mean_user_aov_A - 1.96 * se_aov_A, mean_user_aov_A + 1.96 * se_aov_A)
ci_aov_B = (mean_user_aov_B - 1.96 * se_aov_B, mean_user_aov_B + 1.96 * se_aov_B)

# T-test for AOV (Welch's t-test)
aov_t_stat, aov_p_value = stats.ttest_ind(user_aov_A, user_aov_B, equal_var=False)

# Print Summary Results
print("\n--- RESULTS SUMMARY ---")
print(f"Variant A (Discount): Users = {n_A:,}, Buyers = {buyers_A:,}, Conversion Rate = {cr_A*100:.4f}% (95% CI: {ci_cr_A[0]*100:.4f}% - {ci_cr_A[1]*100:.4f}%)")
print(f"Variant B (Premium):  Users = {n_B:,}, Buyers = {buyers_B:,}, Conversion Rate = {cr_B*100:.4f}% (95% CI: {ci_cr_B[0]*100:.4f}% - {ci_cr_B[1]*100:.4f}%)")
print(f"CR Difference: {(cr_A - cr_B)*100:.4f}% (Relative: {((cr_A - cr_B)/cr_B)*100:.2f}%)")
print(f"CR Z-Test P-value: {cr_p_value:.4g} (Significant: {cr_p_value < 0.05})")

print(f"\nVariant A (Discount): Total Revenue = ${rev_A:,.2f}, RPV = ${rpv_A:.4f} (95% CI: ${ci_rpv_A[0]:.4f} - ${ci_rpv_A[1]:.4f})")
print(f"Variant B (Premium):  Total Revenue = ${rev_B:,.2f}, RPV = ${rpv_B:.4f} (95% CI: ${ci_rpv_B[0]:.4f} - ${ci_rpv_B[1]:.4f})")
print(f"RPV Difference: ${rpv_A - rpv_B:.4f} (Relative: {((rpv_A - rpv_B)/rpv_B)*100:.2f}%)")
print(f"RPV T-Test P-value: {rpv_p_value:.4g} (Significant: {rpv_p_value < 0.05})")

print(f"\nVariant A (Discount): AOV = ${aov_A:.2f} (User AOV Mean: ${mean_user_aov_A:.2f})")
print(f"Variant B (Premium):  AOV = ${aov_B:.2f} (User AOV Mean: ${mean_user_aov_B:.2f})")
print(f"AOV Difference: ${aov_A - aov_B:.2f} (Relative: {((aov_A - aov_B)/aov_B)*100:.2f}%)")
print(f"AOV T-Test P-value: {aov_p_value:.4g} (Significant: {aov_p_value < 0.05})")

# 6. Generate and Save Visualizations
print("\nGenerating charts...")

# Plot 1: Conversion Rate
plt.figure(figsize=(6, 5))
colors = ["#3498db", "#2ecc71"]
bars = plt.bar(
    ['Variant A (Discount)', 'Variant B (Premium)'],
    [cr_A * 100, cr_B * 100],
    color=colors,
    edgecolor='black',
    linewidth=1.2,
    width=0.6
)
plt.errorbar(
    x=[0, 1],
    y=[cr_A * 100, cr_B * 100],
    yerr=[[ (cr_A - ci_cr_A[0])*100, (cr_B - ci_cr_B[0])*100 ], [ (ci_cr_A[1] - cr_A)*100, (ci_cr_B[1] - cr_B)*100 ]],
    fmt='none',
    c='black',
    capsize=8,
    elinewidth=1.5
)
plt.title("Conversion Rate Comparison (with 95% CI)", pad=15)
plt.ylabel("Conversion Rate (%)")
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval + 0.08, f"{yval:.3f}%", ha='center', fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(artifacts_dir, "conversion_rate.png"), dpi=150)
plt.close()

# Plot 2: Average Order Value
plt.figure(figsize=(6, 5))
bars = plt.bar(
    ['Variant A (Discount)', 'Variant B (Premium)'],
    [mean_user_aov_A, mean_user_aov_B],
    color=colors,
    edgecolor='black',
    linewidth=1.2,
    width=0.6
)
plt.errorbar(
    x=[0, 1],
    y=[mean_user_aov_A, mean_user_aov_B],
    yerr=[[ (mean_user_aov_A - ci_aov_A[0]), (mean_user_aov_B - ci_aov_B[0]) ], [ (ci_aov_A[1] - mean_user_aov_A), (ci_aov_B[1] - mean_user_aov_B) ]],
    fmt='none',
    c='black',
    capsize=8,
    elinewidth=1.5
)
plt.title("Average Order Value Comparison (with 95% CI)", pad=15)
plt.ylabel("Average Order Value ($)")
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval + 3.0, f"${yval:.2f}", ha='center', fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(artifacts_dir, "average_order_value.png"), dpi=150)
plt.close()

# Plot 3: Revenue per Visitor
plt.figure(figsize=(6, 5))
bars = plt.bar(
    ['Variant A (Discount)', 'Variant B (Premium)'],
    [rpv_A, rpv_B],
    color=colors,
    edgecolor='black',
    linewidth=1.2,
    width=0.6
)
plt.errorbar(
    x=[0, 1],
    y=[rpv_A, rpv_B],
    yerr=[[ (rpv_A - ci_rpv_A[0]), (rpv_B - ci_rpv_B[0]) ], [ (ci_rpv_A[1] - rpv_A), (ci_rpv_B[1] - rpv_B) ]],
    fmt='none',
    c='black',
    capsize=8,
    elinewidth=1.5
)
plt.title("Revenue per Visitor Comparison (with 95% CI)", pad=15)
plt.ylabel("Revenue per Visitor ($)")
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval + 0.05, f"${yval:.2f}", ha='center', fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(artifacts_dir, "revenue_per_visitor.png"), dpi=150)
plt.close()

print(f"Charts successfully generated and saved to {artifacts_dir}.")

# 7. Write a summary JSON file for reporting
import json
metrics = {
    "Variant A": {
        "Name": "Discount-focused banner ('50% OFF Today')",
        "Users": int(n_A),
        "Buyers": int(buyers_A),
        "ConversionRate": float(cr_A),
        "ConversionRate_CI": [float(ci_cr_A[0]), float(ci_cr_A[1])],
        "TotalRevenue": float(rev_A),
        "RPV": float(rpv_A),
        "RPV_CI": [float(ci_rpv_A[0]), float(ci_rpv_A[1])],
        "TotalPurchases": int(purchases_A),
        "AOV": float(aov_A),
        "UserAOV_Mean": float(mean_user_aov_A),
        "UserAOV_CI": [float(ci_aov_A[0]), float(ci_aov_A[1])]
    },
    "Variant B": {
        "Name": "Premium-quality messaging ('Trusted by 1 Million Customers')",
        "Users": int(n_B),
        "Buyers": int(buyers_B),
        "ConversionRate": float(cr_B),
        "ConversionRate_CI": [float(ci_cr_B[0]), float(ci_cr_B[1])],
        "TotalRevenue": float(rev_B),
        "RPV": float(rpv_B),
        "RPV_CI": [float(ci_rpv_B[0]), float(ci_rpv_B[1])],
        "TotalPurchases": int(purchases_B),
        "AOV": float(aov_B),
        "UserAOV_Mean": float(mean_user_aov_B),
        "UserAOV_CI": [float(ci_aov_B[0]), float(ci_aov_B[1])]
    },
    "StatisticalTests": {
        "ConversionRate": {
            "Z_Stat": float(z_stat),
            "P_Value": float(cr_p_value),
            "Significant": bool(cr_p_value < 0.05)
        },
        "RevenuePerVisitor": {
            "T_Stat": float(rpv_t_stat),
            "P_Value": float(rpv_p_value),
            "Significant": bool(rpv_p_value < 0.05)
        },
        "AverageOrderValue": {
            "T_Stat": float(aov_t_stat),
            "P_Value": float(aov_p_value),
            "Significant": bool(aov_p_value < 0.05)
        }
    }
}

with open(os.path.join(artifacts_dir, "metrics.json"), "w") as f:
    json.dump(metrics, f, indent=4)

# 8. Save prepared CSV for Tableau
tableau_csv_path = "/Users/jhanvimattil/ecommerce-ab/ab_test_user_summary.csv"
print(f"Saving prepared A/B test summary dataset to {tableau_csv_path}...")
tableau_df = user_stats[['user_id', 'group', 'total_views', 'total_carts', 'sim_purchases', 'sim_revenue', 'is_buyer']].rename(
    columns={
        'sim_purchases': 'purchases',
        'sim_revenue': 'revenue'
    }
)
tableau_df.to_csv(tableau_csv_path, index=False)
print(f"CSV saved successfully at {tableau_csv_path}!")

print("Analysis completed successfully!")
print(f"Total time elapsed: {time.time() - start_time:.2f} seconds.")
