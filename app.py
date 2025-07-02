import plotly.express as px
from shiny import App, render, ui, reactive
from shinywidgets import render_plotly
import pandas as pd
import faicons as fa

# ------------------- Load the data -------------------

df = pd.read_csv("merged_water_quality_weather.csv")
df["date"] = pd.to_datetime(df["date"])
min_date = df["date"].min().date()
max_date = df["date"].max().date()

regions = df["region"].unique().tolist()
councils = df["council"].unique().tolist()


ICONS = {
    "user": fa.icon_svg("user", "regular"),
    "wallet": fa.icon_svg("wallet"),
    "hourglass": fa.icon_svg("hourglass", "solid"),
}

# ------------------- Create the UI -------------------

app_ui = ui.page_fluid(
    ui.navset_tab(  
        ui.nav_panel("Sydney Beach Water Quality Dashboard",  
            ui.layout_sidebar(
                ui.sidebar(
                            ui.div( ui.h3("Filters"),
                                    ui.input_date_range("daterange", "Select Date range", start=min_date, end=max_date, format="yyyy-mm-dd"),
                                    ui.br(),
                                    ui.input_checkbox_group(  
                                        "regions",  
                                        "Select Regions",  
                                        choices=regions,
                                        selected=[],  # Default selection of first three regions
                                    ),
                                    ui.br(),
                                    ui.input_selectize(
                                    "councils",
                                    "Select Councils",
                                    choices=councils,
                                    selected=[],
                                    multiple=True
                                                ),
                                    ui.br(),
                                    ui.download_button("download_data", "Download Data", class_="btn-primary", style="width: 100%;")
                            ), bg ="#035f86"),
                                ui.layout_column_wrap(
                                        ui.value_box(
                                            "Total Number of Beaches",
                                            "100",
                                            showcase=ICONS["user"],
                                            theme="bg-gradient-orange-red",
                                            full_screen=True,
                                        ),
                                        ui.value_box(
                                            "Most Polluted Beach",
                                            "Bondi Beach",
                                            showcase=ICONS["wallet"],
                                            theme="text-green",
                                            showcase_layout="top right",
                                            full_screen=True,
                                        ),
                                        ui.value_box(
                                            "The Cleanest Beach",
                                            "Manly Beach",
                                            showcase=ICONS["hourglass"],
                                            theme="purple",
                                            showcase_layout="bottom",
                                            full_screen=True,
                                        ),
                                    ),
                                    # Charts
                                ui.div(class_="graph-section"),
                                    ui.layout_column_wrap(width = 1/2),
                                        ui.card(),
                                            ui.card_header(),
                                    
                                        ui.card(),
                                            ui.card_header(),

                    )
            ),
        ui.nav_panel("Data", "Page B content"),  
        ui.nav_panel("FAQ", "Page C content"),
        id="page"  )
    )




def server(input, output, session):
    pass


app = App(app_ui, server)