<div align="center">

![project logo](https://user-images.githubusercontent.com/76540311/217404630-863299b2-1b21-4ae7-8330-28f980be614f.png)


# Fire and Smoke Digital Twin: Backend
See the [Frontend](https://github.com/UrbanInfoLab/FireIncidentFrontend) or the [API](https://github.com/UrbanInfoLab/FireIncidentData) for more details.

[![latest release badge]][latest release link] [![github stars badge]][github stars link] [![github forks badge]][github forks link]

[![CI checks on main badge]][CI checks on main link] [![latest commit to main badge]][latest commit to main link]

[![github open issues badge]][github open issues link] [![github open prs badge]][github open prs link]

[CI checks on main badge]: https://flat.badgen.net/github/checks/urbaninfolab/FireIncidentBackend/main?label=CI%20status%20on%20main&cache=900&icon=github
[CI checks on main link]: https://github.com/urbaninfolab/FireIncidentBackend/actions/workflows/test-invoke-conda.yml
[github forks badge]: https://flat.badgen.net/github/forks/urbaninfolab/FireIncidentBackend?icon=github
[github forks link]: https://useful-forks.github.io/?repo=urbaninfolab%2FFireIncidentBackend
[github open issues badge]: https://flat.badgen.net/github/open-issues/urbaninfolab/FireIncidentBackend?icon=github
[github open issues link]: https://github.com/urbaninfolab/FireIncidentBackend/issues?q=is%3Aissue+is%3Aopen
[github open prs badge]: https://flat.badgen.net/github/open-prs/urbaninfolab/FireIncidentBackend?icon=github
[github open prs link]: https://github.com/urbaninfolab/FireIncidentBackend/pulls?q=is%3Apr+is%3Aopen
[github stars badge]: https://flat.badgen.net/github/stars/urbaninfolab/FireIncidentBackend?icon=github
[github stars link]: https://github.com/urbaninfolab/FireIncidentBackend/stargazers
[latest commit to main badge]: https://flat.badgen.net/github/last-commit/urbaninfolab/FireIncidentBackend/main?icon=github&color=yellow&label=last%20dev%20commit&cache=900
[latest commit to main link]: https://github.com/urbaninfolab/FireIncidentBackend/commits/main
[latest release badge]: https://flat.badgen.net/github/release/urbaninfolab/FireIncidentBackend/development?icon=github
[latest release link]: https://github.com/urbaninfolab/FireIncidentBackend/releases

</div>

The Fire and Smoke Digital Twin Backend is the engine that drives our real-time fire incident visualization platform. It consists of web scrapers for over twenty different fire departments, responsible for unifying their data formats into our collection format. All data is backed up and made publicly accessible via our [FireIncidentAPI](https://github.com/UrbanInfoLab/FireIncidentData).

Our backend system not only collects data but also generates smoke fallouts using VSmoke and MantaFlow fluid simulations at one hour, two hour, and three hour marks. 

The `Backend2D` folder contains scripts for fetching live fire information from selected city fire departments and converting it to our unified format. After fetching the data, it runs the VSmoke smoke simulation to generate an approximate smoke path for each fire. This operation is swift, taking less than a second for each fire incident.

To run the 2D backend, execute the following command:

```bash
python events.py fireMap<City>
```

Here, `<City>` should be replaced with your chosen city, such as `Houston`, `Dallas`, or `LosAngeles`. See our City Coverage below.

The `Backend3D` folder, on the other hand, works with the fetched fire information to conduct a more accurate fluid simulation using MantaFlow and Blender. The MantaFlow fluid simulation takes into account all fire characteristics sourced from the fire department data, resulting in a highly accurate smoke path prediction.

To run the 3D backend, execute the following command:

```bash
blender austin.blend -P spawnFires.py
```

This command opens Blender with Austin's city geometry loaded in and initiates the fluid simulation. If you want to work with custom fire data or a different city, you can edit parts of the `spawnFires.py` script and replace `austin.blend` with your city's dataset. 

We recommend a more general approach of fetching 3D tiles for each fire so that custom datasets do not need to be maintained. However, this method can slow down the entire pipeline, especially for cities where the 3D data changes infrequently. For future work, we suggest creating a local cache of 3D city data tiles from OpenStreetMaps3D, which can be gridded and fetched for each fire incident. This approach would be efficient and accurate for on-demand smoke simulations, regardless of the fire location.

## Coverage

We are currently collecting and publishing active fire data from the following cities:             

| City Name | Collection Start Date |      
| --------------- | --------------- |
| Austin, Texas | February 1, 2022 |
| Dallas, Texas | July 6, 2022 |
| El Paso, Texas | July 17, 2022 |
| Houston, Texas | July 6, 2022 |
| Los Angeles, California | July 18, 2022 |
| Miami, Florida | January 23, 2023 |
| Milwaukee, Wisconsin | January 23, 2023 |
| Orlando, Florida | January 23, 2023 |
| Portland, Oregon | January 23, 2023 |
| Riverside, California | July 17, 2022 |
| San Antonio, Texas | July 7, 2022 |
| San Antonio, Texas | July 7, 2022 |
| San Diego, California | September 8, 2022 |
| Seattle, Washington | July 19, 2022 |

This table is sorted alphabetically by city.

Please note that due to some outages, we are missing data for a few days out of the year of 2022. Please keep this in mind when using the data.

# Contributors

The Fire and Smoke Digital Twin Backend is a collaborative project by the [Urban Information Lab](https://sites.utexas.edu/uil) and numerous other contributors. We extend our heartfelt thanks to all those involved for their time and dedication. A complete list of these remarkable contributors can be found [here](https://github.com/urbaninfolab/FireIncidentBackend/collaborators).

As we continue to develop and refine our platform, we welcome contributions. If you're interested in contributing, please take a look at our open issues and pull requests.
