import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

df = pd.read_csv('experiment_with_costs.csv')
if 'test_no' in df.columns:
    df.drop(columns=['test_no'], inplace=True)

# Ensure we use the first 4 cols as search costs and the next 4 as final costs
cols = df.columns.tolist()
n_alg = 4
search_cols = cols[:n_alg]
final_cols = cols[n_alg:n_alg + n_alg]

# Desired algorithm order / labels
alg_order = ['BFS', 'DFS', 'A*', 'Greedy']

# Build dataframes and rename columns to the target algorithm names (by position)
df_search = df[search_cols].copy()
df_search.columns = alg_order

df_final = df[final_cols].copy()
df_final.columns = alg_order

# Melt for seaborn violin plotting
search_melt = df_search.melt(var_name='Algorithm', value_name='Cost')
final_melt = df_final.melt(var_name='Algorithm', value_name='Cost')

plt.style.use('seaborn-v0_8-whitegrid')
fig, axes = plt.subplots(1, 2, figsize=(10, 5))

# Left: Violin plot of search costs (per-algorithm distribution)
sns.violinplot(x='Algorithm', y='Cost', data=search_melt, order=alg_order,
               inner='quartile', palette='Set3', ax=axes[0])
sns.swarmplot(x='Algorithm', y='Cost', data=search_melt, order=alg_order,
              color='k', size=3, ax=axes[0], alpha=0.6)
axes[0].set_title('Search Cost Distribution per Algorithm', fontsize=12)
axes[0].set_ylabel('Search Cost', fontsize=11)
axes[0].set_xlabel('')
axes[0].set_xticklabels(alg_order, fontweight='bold', fontsize=11)

# Right: Violin plot of final solution costs (per-algorithm distribution)
sns.violinplot(x='Algorithm', y='Cost', data=final_melt, order=alg_order,
               inner='quartile', palette='Set3', ax=axes[1])
sns.swarmplot(x='Algorithm', y='Cost', data=final_melt, order=alg_order,
              color='k', size=3, ax=axes[1], alpha=0.6)
axes[1].set_title("Final Solution Cost Distribution per Algorithm", fontsize=12)
axes[1].set_ylabel('Final Path Cost', fontsize=11)
axes[1].set_xlabel('')
axes[1].set_xticklabels(alg_order, fontweight='bold', fontsize=11)

plt.tight_layout()
plt.show()