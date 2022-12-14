import pandas as pd
import numpy as np
# pylcaio implementation requirements
from collections import defaultdict

def identify_rest_of_world_regions(
    df_in: pd.DataFrame,
    list_io_countries: list,
    dict_io_countries_per_lca_region: dict
) -> pd.DataFrame:
    # Identify the rest of the world regions

    # create dataframe copy to ensure the input dataframe is not manipulated (else repeated exection will likely fail)
    df = df_in.copy()

    # get array of those master activities (key 'activityNameId') where one defined geography is 'RoW'
    master_activities_with_rest_of_world_geography = pd.DataFrame(df[df['io_geography'] == 'RoW']['activityNameId'])
    # copy dataframe index (='index') to column for merging later
    master_activities_with_rest_of_world_geography['index'] = master_activities_with_rest_of_world_geography.index
    
    # replace LCA regions (eg. 'Europe without Switzerland') with the associated IO countries (eg. '"AT", "BE", "BG", ...')
    df['io_geography'] = df['io_geography'].map(dict_io_countries_per_lca_region).fillna(df['io_geography'])

    # remove all activities associated with master activities for which no defined geography is 'RoW'
    df_rest_of_world = df[df['activityNameId'].isin(master_activities_with_rest_of_world_geography['activityNameId'])]
    # remove all activities where 'io_geography' == 'RoW' to ensure 'RoW' does not appear in aggregation
    df_rest_of_world = df_rest_of_world.drop(master_activities_with_rest_of_world_geography['index'])

    # aggregate by master activities (key 'activityNameId')
    df_rest_of_world_agg = pd.DataFrame(data = df_rest_of_world.groupby('activityNameId')['io_geography'].apply(tuple))
    # copy dataframe index (='activityNameId') to column for merging later
    df_rest_of_world_agg.reset_index(inplace = True)
    # add activity index column to aggregate dataframe for dataframe update later
    df_rest_of_world_agg = df_rest_of_world_agg.merge(
        right = master_activities_with_rest_of_world_geography,
        how = 'left',
        on = 'activityNameId'
    )
    # set activity index column as dataframe index for dataframe update later
    df_rest_of_world_agg.set_index(keys = 'index', inplace = True)

    # calculate 'rest of world' region per activity
    df_rest_of_world_agg['io_geography_rest_of_world'] = df_rest_of_world_agg.apply(
        lambda row: tuple(set(list_io_countries) - set(row['io_geography'])), #https://stackoverflow.com/a/53343046
        axis = 1
    )
    # remove activities where 'rest of world' region is null because all countries are described
    df_rest_of_world_agg = df_rest_of_world_agg.dropna(subset ='io_geography_rest_of_world')

    # enumerate unique rest of world regions
    df_rest_of_world_agg['io_geography'] = pd.factorize(df_rest_of_world_agg['io_geography_rest_of_world'])[0]
    df_rest_of_world_agg['io_geography'] = 'RoW_' + df_rest_of_world_agg['io_geography'].astype(str)
    
    df.update(
        other = df_rest_of_world_agg['io_geography'],
        overwrite = True
    )

    return df


def calc_productions(self):
    """ Calculates the different total productions for either countries, regions or RoWs

    Returns:
    -------
        The updated self.total_prod_country, self.total_prod_region and self.total_prod_RoW dataframe

    """

    # the user needs to determine the total demand before being able to calculate productions
    listdrop = []

    absent_countries = {}
    for i in range(0, len(list(self.countries_per_regions.values()))):
        absent_country = [item for item in self.listcountry if
                            item not in list(self.countries_per_regions.values())[i]]
        absent_countries[list(self.countries_per_regions.keys())[i]] = absent_country

    self.total_prod_country =  pd.DataFrame(
        self.X_io.todense(), index=pd.MultiIndex.from_product([self.regions_of_IO, self.sectors_of_IO],
                                                                names=['region', 'sector']), columns=['production'])

    listmatrixxx = []
    listlisteee = []
    listdfff = []
    for i in range(0, len(absent_countries)):
        listmatrixxx.append('matrixxx' + str(i))
        listlisteee.append('listeee' + str(i))
        listdfff.append('dfff' + str(i))
    listact = []
    for i in range(0, self.number_of_products_IO):
        listact.append(self.total_prod_country.index[i][1])
    for i in range(0, len(list(absent_countries.values()))):
        listadd = []
        listmatrixxx[i] = self.total_prod_country.drop(list(absent_countries.values())[i], axis=0, level=0)
        for k in range(0, self.number_of_products_IO):
            somme = 0
            for j in range(0, len(listmatrixxx[i]), self.number_of_products_IO):
                somme += listmatrixxx[i].iloc[j + k, 0]
            listadd.append(somme)
        listlisteee[i] = listadd
        listdfff[i] = pd.DataFrame(listlisteee[i], listact, [list(absent_countries.keys())[i]])
        self.total_prod_region = self.total_prod_region.join(listdfff[i], how='outer')

    # next step we will consider the rest-of-the-World geographies, so the user has to run 'identify_RoWs' first
    if len(self.dictRoW) == 0:
        print('You need to run "identify_rows" before calculating the productions')
        return

    listmatrixxxx = []
    listlisteeee = []
    listdffff = []
    for k in range(0, len(list(self.dictRoW.keys()))):
        listmatrixxxx.append('matrixxxx' + str(k))
        listlisteeee.append('listeeee' + str(k))
        listdffff.append('dfff' + str(k))
        listdrop = []
        for i in range(0, len(self.dictRoW)):
            listadd = []
            for j in range(0, len(self.listcountry)):
                if self.listcountry[j] not in list(self.dictRoW.values())[i]:
                    listadd.append(self.listcountry[j])
            listdrop.append(listadd)

    for i in range(0, len(list(self.dictRoW.keys()))):
        listadd = []
        listmatrixxxx[i] = self.total_prod_country.drop(listdrop[i], axis=0, level=0)
        for k in range(0, self.number_of_products_IO):
            somme = 0
            for j in range(0, len(listmatrixxxx[i]), self.number_of_products_IO):
                somme += listmatrixxxx[i].iloc[j + k, 0]
            listadd.append(somme)
        listlisteeee[i] = listadd
        listdffff[i] = pd.DataFrame(listlisteeee[i], listact, [list(self.dictRoW.keys())[i]])
        self.total_prod_RoW = self.total_prod_RoW.join(listdffff[i], how='outer')


def replace_lca_data_with_io_data_electricity_prices(
    df_in: pd.DataFrame
) -> pd.DataFrame:

    df = df_in.copy()

    condition_1: pd.Series = df['price'] == 0.0977
    condition_2: pd.Series = df['productName'] == 'electricity'

    df_subset = df[condition_1, condition_2][['io_geography', 'price']]
    df_subset_updated = df_subset.merge(
        right = electricity_prices,
        left_on = io_geography,
        right_on = 'region',
        how = 'left'
    )

    df = df.update(df_subset_updated)
    
    return df


def update_prices_electricity(self):
    """ Method specially for ecoinvent and exiobase, in which electricity prices from ecoinvent are replaced by
        price extracted from exiobase

        Returns:
        -------
        The updated price column of the self.PRO_f matrix

        """

    electricity_price = pd.read_excel(pkg_resources.resource_stream(__name__,
                                                                    '/Data/Regionalized_electricity_prices.xlsx'),
                                                                    index_col=0)

    electricity_processes = self.PRO_f.price.loc[
        [i for i in self.PRO_f.index if
            (0.0977 == self.PRO_f.price[i] and 'electricity' in self.PRO_f.productName[i]) or
            (0.107 == self.PRO_f.price[i] and 'electricity' in self.PRO_f.productName[i])]]

    if electricity_processes.empty:
        print('Empty!')
        return
    merged = self.PRO_f.loc[electricity_processes.index.values, ['price', 'io_geography']].merge(
        electricity_price, left_on=['io_geography'], right_on=electricity_price.index, how='left')
    merged.prices[merged.prices.isnull()] = merged.price
    merged.index = electricity_processes.index.values
    merged = merged.drop(['price', 'io_geography'], axis=1)
    self.PRO_f.price.update(merged.prices)


def calc_productions(self):
        """ Calculates the different total productions for either countries, regions or RoWs

        Returns:
        -------
            The updated self.total_prod_country, self.total_prod_region and self.total_prod_RoW dataframe

        """

        # the user needs to determine the total demand before being able to calculate productions
        listdrop = []

        absent_countries = {}
        for i in range(0, len(list(self.countries_per_regions.values()))):
            absent_country = [item for item in self.listcountry if
                              item not in list(self.countries_per_regions.values())[i]]
            absent_countries[list(self.countries_per_regions.keys())[i]] = absent_country

        self.total_prod_country =  pd.DataFrame(
            self.X_io.todense(), index=pd.MultiIndex.from_product([self.regions_of_IO, self.sectors_of_IO],
                                                                  names=['region', 'sector']), columns=['production'])

        listmatrixxx = []
        listlisteee = []
        listdfff = []
        for i in range(0, len(absent_countries)):
            listmatrixxx.append('matrixxx' + str(i))
            listlisteee.append('listeee' + str(i))
            listdfff.append('dfff' + str(i))
        listact = []
        for i in range(0, self.number_of_products_IO):
            listact.append(self.total_prod_country.index[i][1])
        for i in range(0, len(list(absent_countries.values()))):
            listadd = []
            listmatrixxx[i] = self.total_prod_country.drop(list(absent_countries.values())[i], axis=0, level=0)
            for k in range(0, self.number_of_products_IO):
                somme = 0
                for j in range(0, len(listmatrixxx[i]), self.number_of_products_IO):
                    somme += listmatrixxx[i].iloc[j + k, 0]
                listadd.append(somme)
            listlisteee[i] = listadd
            listdfff[i] = pd.DataFrame(listlisteee[i], listact, [list(absent_countries.keys())[i]])
            self.total_prod_region = self.total_prod_region.join(listdfff[i], how='outer')

        # next step we will consider the rest-of-the-World geographies, so the user has to run 'identify_RoWs' first
        if len(self.dictRoW) == 0:
            print('You need to run "identify_rows" before calculating the productions')
            return

        listmatrixxxx = []
        listlisteeee = []
        listdffff = []
        for k in range(0, len(list(self.dictRoW.keys()))):
            listmatrixxxx.append('matrixxxx' + str(k))
            listlisteeee.append('listeeee' + str(k))
            listdffff.append('dfff' + str(k))
            listdrop = []
            for i in range(0, len(self.dictRoW)):
                listadd = []
                for j in range(0, len(self.listcountry)):
                    if self.listcountry[j] not in list(self.dictRoW.values())[i]:
                        listadd.append(self.listcountry[j])
                listdrop.append(listadd)

        for i in range(0, len(list(self.dictRoW.keys()))):
            listadd = []
            listmatrixxxx[i] = self.total_prod_country.drop(listdrop[i], axis=0, level=0)
            for k in range(0, self.number_of_products_IO):
                somme = 0
                for j in range(0, len(listmatrixxxx[i]), self.number_of_products_IO):
                    somme += listmatrixxxx[i].iloc[j + k, 0]
                listadd.append(somme)
            listlisteeee[i] = listadd
            listdffff[i] = pd.DataFrame(listlisteeee[i], listact, [list(self.dictRoW.keys())[i]])
            self.total_prod_RoW = self.total_prod_RoW.join(listdffff[i], how='outer')