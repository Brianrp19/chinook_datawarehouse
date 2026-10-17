from prefect import flow

@flow(name="Chinook ETL Data Warehouse", log_prints=True)
def etl_chinook():
    print("levantando pagina")


if __name__ == "__main__":
    etl_chinook.serve(
        name="chinook-local",
        limit=1,
    )
