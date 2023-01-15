# A Docker image for hosting the cad_to_dagmc web app at https://www.xsplot.com

# build with
# docker build -t cad_to_dagmc .

# run with
# docker run --network host -t cad_to_dagmc

# maintained at https://github.com/fusion_energy/cad_to_dagmc.com/

FROM continuumio/miniconda3:4.12.0

RUN conda install -c conda-forge openmc

COPY src/*.py .
COPY pyproject.toml .

RUN pip install .[gui]

ENV PORT 8501

EXPOSE 8501


# solves bug of streamlit not running in container
# https://github.com/streamlit/streamlit/issues/4842
ENTRYPOINT [ "streamlit", "run" ]
CMD [ "app.py", "--server.headless", "true", "--server.fileWatcherType", "none", "--browser.gatherUsageStats", "false"]
