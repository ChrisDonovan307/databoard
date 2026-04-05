# import pandas as pd

# df = pd.read_csv('data/installations/installations.csv')

# df.columns
# df.info()

# continents = list(df.continent.unique())
# type(continents)
# continents.append('All')

# continents = ['All'] += df.continent.unique()
# type(continents)
# print(continents)

# first_list = ['a', 'b']
# first_list.append('c')
# # second_list = [first_list, 'c']
# print(first_list)
# print(second_list)


##########################

import pandas as pd
df = pd.read_csv('backend/data/installations/installations.csv', usecols=['country', 'name'])
# df.groupby('country').agg('count').sort_values('name', ascending=False)
df.groupby('country').agg(
    country=('country', 'first'),
    count=('country', 'count')
).sort_values('count', ascending=False)
