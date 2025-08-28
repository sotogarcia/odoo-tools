## Synopsis

Modules used to extend Odoo funcionality


## Motivation

I needed to group modules whose functionality was not related to each other.

## Installation

Project can be cloned on your server using git command line, following line is
an example:

```
git clone https://github.com/sotogarcia/odoo-tools.git
```

Once you have downloaded the project, you will can find the modules inside
project folder, to install them in Odoo you must copy folders into the addons
directory, alongside the official modules.

Once done, you need to update the module list before these new modules are
available to install.

For this you need the Technical menu enabled, since the Update Modules List
menu option is provided by it. It can be found in the Modules section of the
Settings menu.

After running the modules list update you can confirm the new modules are
available to install. In the Local Modules list, remove the Apps filter and
search for department. You should see the new modules available.


## Modules

```
└──odoo-tools
    ├───assets      : non-software development resources
    ├───modules     : business logic to enhance the Odoo existing functionality
    └───project     : UML schemas and project notes
```

## Licences

* Code is licensed under the GNU AFFERO GENERAL PUBLIC LICENSE (V 3).
To view a copy of this license, visit [http://www.gnu.org/licenses/agpl-3.0.html](http://www.gnu.org/licenses/agpl-3.0.html).

* [![Creative Commons License](https://i.creativecommons.org/l/by-nc-sa/4.0/80x15.png)](http://creativecommons.org/licenses/by-nc/4.0/)
All the documentation is licensed under a [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](http://creativecommons.org/licenses/by-nc-sa/4.0/).


## Feedback

The best way to send feedback is to file an issue at [https://github.com/sotogarcia/odoo-tools/issues](https://github.com/sotogarcia/ /issues) or to reach out to us via [twitter](https://twitter.com/jorgedenarahio) or [email](sotogarcia@gmail.com).
