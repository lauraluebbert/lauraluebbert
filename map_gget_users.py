# References:
# https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart-client-libraries
# https://geopandas.org/en/stable/docs/user_guide/mapping.html

# Packages to fetch data from GA instance
import os
import sys
import json
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)

# Packages for plotting
import pandas as pd
import geopandas
import country_converter as coco
import matplotlib
import matplotlib.pyplot as plt


def sample_run_report(
    property_id,
    datatype="activeUsers",
    dimension="country",
    start_date="30daysAgo",
    end_date="today",
):
    """
    Returns the number of [datatype] per [dimension] from [start_date] to [end_date]
    from a Google Analytics 4 property (defined by [property_id]).
    """

    # Using a default constructor instructs the client to use the credentials
    # specified in GOOGLE_APPLICATION_CREDENTIALS environment variable
    client = BetaAnalyticsDataClient()

    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name=dimension)],
        metrics=[Metric(name=datatype)],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )
    response = client.run_report(request)

    return response


def get_GA_data(property_id, ga_creds):
    """
    Wrapper function to fetch and clean up data returned by the sample_run_report function.
    """
    # Save GA credentials dictionary to json and set as environment variable
    with open("ga_creds.json", "w") as outfile:
        json.dump(ga_creds, outfile)
        
    print(ga_creds)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "ga_creds.json"

    response = sample_run_report(property_id)

    countries = []
    counts = []
    for row in response.rows:
        countries.append(row.dimension_values[0].value)
        counts.append(row.metric_values[0].value)

    df = pd.DataFrame()
    df["country"] = countries
    df["user_count"] = counts

    # Delete GA credentials environment variable
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    # Delete GA creds json
    os.remove("ga_creds.json")

    return df


def plot_gget_user(property_id, ga_creds):
    """
    Plot number of visitors to the gget visitors during the last 30 days
    by country.
    """
    # Get latest data from gget GA property
    df = get_GA_data(property_id, ga_creds)

    # Load world dataframe
    world = geopandas.read_file(geopandas.datasets.get_path("naturalearth_lowres"))

    # Drop Antarctica because it takes up a lot of space on the map
    world = world[(world.pop_est > 0) & (world.name != "Antarctica")]

    # Convert country names to ISO3 standard
    df["iso_a3"] = coco.convert(df["country"].values, to="ISO3")

    # Add user counts to world data frame and replace NaNs with 0s
    world = pd.merge(world, df, how="left", on="iso_a3").fillna(0)
    world["user_count"] = world["user_count"].astype(int)

    # # Uncomment if you want to add country name labels
    # # Get coordinates from polygon for country labels
    # world["coords"] = world["geometry"].apply(
    #     lambda x: x.representative_point().coords[:]
    # )
    # world["coords"] = [coords[0] for coords in world["coords"]]
    # # Add column defining whether user count > 0
    # world["show_name"] = world["user_count"] > 0

    # Create world plot
    fig, ax = plt.subplots(1, figsize=(20, 10))

    fontsize = 15
    col = "user_count"
    cmap = "OrRd"  # Alternative color maps: OrRd YlGn Greens YlOrRd
    vmax = world[col].max()

    # Remove the axes
    ax.axis("off")

    # Define normalization for colormap
    norm = matplotlib.colors.LogNorm(1, vmax)

    # Plot world
    world.plot(
        column=col, ax=ax, edgecolor="lightgrey", linewidth=0.5, cmap=cmap, norm=norm
    )

    # Add colormap legend
    cbaxes = fig.add_axes([0.15, 0.25, 0.01, 0.4])
    cbar = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cbaxes)
    cbar.set_label(label="Number of active users", size=fontsize, labelpad=-65)
    cbar.ax.tick_params(labelsize=fontsize - 2)

#     # Uncomment if you want to add country name labels
#     # Label all countries where user count > 0
#     for idx, row in world[world["show_name"] == True].iterrows():
#         ax.annotate(row["name"], xy=row["coords"], horizontalalignment="center")

#     # Set figure title
#     ax.set_title(
#         "Number of active users of the gget website in the last 30 days",
#         fontsize=fontsize + 2,
#     )

    fig.savefig("gget_user_map.png", bbox_inches="tight", dpi=300, transparent=True)


if __name__ == "__main__" :
    plot_gget_user(property_id=sys.argv[1], ga_creds=sys.argv[2])
