"""
  FIONA
+ YAML
+ JINJA2
+ SPHINX
= DATA DICT
"""

import click
import fiona
import yaml
from jinja2 import Environment, FileSystemLoader, Template

CATEGORY_DESCRIPTOR = "Schema"
ITEM_DESCRIPTOR = "Table"

TEMPLATE_DIR = "./_templates"
TEMPLATE_NAME = "test.template"


class DatasetEntry:
    """Class to hold information about each dataset."""

    def __init__(self, name, columns=None):
        self.name = name
        if columns:
            self.columns = columns
        else:
            self.columns = []

    def __str__(self):
        return "{}: {}".format(self.name, self.columns)

    def __repr__(self):
        return "DatasetEntry({}, {})".format(self.name, self.columns)

    def add_column(self, **kwargs):
        """Create a new ColumnEntry for the DatasetEntry."""
        new_column = ColumnEntry(
            name=kwargs.get("name"),
            data_type=kwargs.get("data_type"),
            length=kwargs.get("length"),
            precision=kwargs.get("precision"),
            scale=kwargs.get("scale"),
            allows_nulls=kwargs.get("allows_nulls"),
            description=kwargs.get("description"),
            order=kwargs.get("order"),
        )
        self.columns.append(new_column)


class ColumnEntry:
    """Class to hold information about each column in the dataset."""

    def __init__(
        self, name, data_type, allows_nulls="Y", description="", order="", length="", precision="", scale="",
    ):
        self.name = name
        if "." in data_type or ":" in data_type:
            self._split_data_type(data_type)
        else:
            self.data_type = data_type
            if length:
                self.length = length
            else:
                self.length = ""
            if precision:
                self.precision = precision
            else:
                self.precision = ""
            if scale:
                self.scale = scale
            else:
                self.scale = ""
        self.allows_nulls = allows_nulls
        self.description = description
        self.order = order

    def __str__(self):
        return f"""
            {self.name}: {self.data_type}, {self.length}, {self.precision}, \
            {self.scale}, {self.allows_nulls}, {self.description}, {self.order}
        """

    def __repr__(self):
        return f"""
            ColumnEntry({self.name}, {self.data_type}, {self.length}, {self.precision}, \
            {self.scale}, {self.allows_nulls}, {self.description}, {self.order})
        """

    def _split_data_type(self, data_type_input: str):
        if "." in data_type_input:
            self.length = ""
            self.precision = data_type_input.split(":")[1].split(".")[0]
            self.scale = data_type_input.split(":")[1].split(".")[1]
            self.data_type = data_type_input.split(":")[0]
        elif ":" in data_type_input:
            self.length = data_type_input.split(":")[1]
            self.precision = ""
            self.scale = ""
            self.data_type = data_type_input.split(":")[0]
        else:
            self.length = ""
            self.precision = ""
            self.scale = ""
            self.data_type = data_type_input


def locate_template(template_dir: str, template_name: str) -> Template:
    """Find the jinja2 template that we're using to format the data dict."""
    env = Environment(loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)
    template = env.get_template(template_name)
    return template


def create_restructured_text(yaml_file: str, name: str) -> None:
    """Create a restructured text file using a template, to be interpreted by Sphinx."""
    config_data = yaml.safe_load(open(yaml_file))
    template = locate_template(TEMPLATE_DIR, TEMPLATE_NAME)

    with open(f"./{name}.rst", "w") as rstfile:
        rendered_dict = template.render(config_data)
        rstfile.write(rendered_dict)


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option(
    "-f", "--file", type=str, help="Create a yaml file representing the structure of this geospatial file.",
)
@click.option("--no_rst", is_flag=True, help="Create a restructedtext representation.")
@click.option(
    "--rst_only", type=str, help="Create a restructured text file from the supplied yaml file.",
)
@click.pass_context
def main(ctx: click.Context, file: str, load: bool, createyaml: bool, no_rst: bool, rst_only: str) -> None:
    """Create an online data dictionary from a geospatial data source."""

    if rst_only:
        create_restructured_text(rst_only, "temp")
        click.secho(f"./temp.rst created.", fg="green")

    elif file:

        # Interrogate the supplied file using Fiona
        with fiona.open(file) as src:
            meta = src.meta
            data = meta["schema"]["properties"]
            data_dict = dict(data)

            dataset = DatasetEntry(src.name)
            for item in data_dict.items():
                dataset.add_column(name=item[0], data_type=item[1])

            yaml_columns = []
            auto_order = 1

            for column in dataset.columns:
                yaml_columns.append(
                    {
                        "name": column.name,
                        "data_type": column.data_type,
                        "length": column.length,
                        "precision": column.precision,
                        "scale": column.scale,
                        "allows_nulls": "F",
                        "description": "Update this with an actual description.",
                        "order": auto_order,
                    }
                )
                auto_order += 1
            yaml_content = {
                "category_descriptor": CATEGORY_DESCRIPTOR,
                "item_descriptor": ITEM_DESCRIPTOR,
                "categories": [
                    {
                        "name": src.name,
                        "description": "This is a test dataset.",
                        "contains": [
                            {"name": dataset.name, "description": "This is a test table.", "contains": yaml_columns,}
                        ],
                    }
                ],
            }
            click.echo(yaml_content)

        # Create the .yml file
        with open(f"./{src.name}.yml", "w") as yaml_file:
            yaml.dump(yaml_content, yaml_file, default_flow_style=False, sort_keys=False)
        click.secho(f"./{src.name}.yml created.", fg="green")

        if not no_rst:
            create_restructured_text(f"./{src.name}.yml", src.name)
            click.secho(f"./{src.name}.rst created.", fg="green")
        else:
            click.secho("No .rst file created.", fg="red")

    else:
        raise FileNotFoundError("Missing -f or --file option with string pointing to a valid file.")

    ctx.exit(0)


if __name__ == "__main__":
    # @click.command edits our main() functions parameters, pylint doesn't know
    # pylint: disable=no-value-for-parameter
    main()
