from core.command_param_types import Any, Int
from core.decorators import instance, command
from core.chat_blob import ChatBlob


@instance()
class NanoController:
    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.text = registry.get_instance("text")

    @command(command="nano", params=[Any("search")], access_level="all",
             description="Search for a nano")
    def nano_cmd(self, channel, sender, reply, args):
        search = args[0]

        sql = "SELECT n1.lowid, n1.lowql, n1.name, n1.location, n1.profession, n3.id AS nanoline_id, n3.name AS nanoline_name " \
              "FROM nanos n1 " \
              "LEFT JOIN nanos_nanolines_ref n2 ON n1.lowid = n2.lowid " \
              "LEFT JOIN nanolines n3 ON n2.nanolines_id = n3.id " \
              "WHERE n1.name <EXTENDED_LIKE=0> ? " \
              "ORDER BY n1.profession, n3.name, n1.lowql DESC, n1.name ASC"
        data = self.db.query(*self.db.handle_extended_like(sql, [search]))
        cnt = len(data)

        blob = ""
        current_nanoline = -1
        for row in data:
            if current_nanoline != row.nanoline_id:
                if row.nanoline_name:
                    blob += "\n<header2>%s<end> - %s\n" % (row.profession, self.text.make_chatcmd(row.nanoline_name, "/tell <myname> nanolines %d" % row.nanoline_id))
                else:
                    blob += "\n<header2>Unknown/General<end>\n"
                current_nanoline = row.nanoline_id

            blob += "%s [%d] %s\n" % (self.text.make_item(row.lowid, row.lowid, row.lowql, row.name), row.lowql, row.location)
        blob += self.get_footer()

        return ChatBlob("Nano Search Results for '%s' (%d)" % (search, cnt), blob)

    @command(command="nanoloc", params=[], access_level="all",
             description="Show all nano locations")
    def nanoloc_list_cmd(self, channel, sender, reply, args):
        data = self.db.query("SELECT location, COUNT(location) AS cnt FROM nanos GROUP BY location ORDER BY location ASC")

        blob = ""
        for row in data:
            blob += "%s (%d)\n" % (self.text.make_chatcmd(row.location, "/tell <myname> nanoloc %s" % row.location), row.cnt)
        blob += self.get_footer()

        return ChatBlob("Nano Locations", blob)

    @command(command="nanoloc", params=[Any("location")], access_level="all",
             description="Show nanos by location")
    def nanoloc_show_cmd(self, channel, sender, reply, args):
        location = args[0]

        sql = "SELECT n1.lowid, n1.lowql, n1.name, n1.location, n3.profession " \
              "FROM nanos n1 LEFT JOIN nanos_nanolines_ref n2 ON n1.lowid = n2.lowid LEFT JOIN nanolines n3 ON n2.nanolines_id = n3.id " \
              "WHERE n1.location LIKE ? " \
              "ORDER BY n1.profession ASC, n1.name ASC"
        data = self.db.query(sql, [location])
        cnt = len(data)

        blob = ""
        for row in data:
            blob += "%s [%d] %s" % (self.text.make_item(row.lowid, row.lowid, row.lowql, row.name), row.lowql, row.location)
            if row.profession:
                blob += " - <highight>%s<end>" % row.profession
            blob += "\n"

        return ChatBlob("Nanos for Location '%s' (%d)" % (location, cnt), blob)

    @command(command="nanolines", params=[], access_level="all",
             description="Show nanos by nanoline")
    def nanolines_list_cmd(self, channel, sender, reply, args):
        data = self.db.query("SELECT DISTINCT profession FROM nanolines ORDER BY profession ASC")

        blob = ""
        for row in data:
            blob += self.text.make_chatcmd(row.profession, "/tell <myname> nanolines %s" % row.profession) + "\n"
        blob += self.get_footer()

        return ChatBlob("Nanolines", blob)

    @command(command="nanolines", params=[Int("nanoline_id")], access_level="all",
             description="Show nanos by nanoline id")
    def nanolines_id_cmd(self, channel, sender, reply, args):
        nanoline_id = args[0]
        nanoline = self.db.query_single("SELECT * FROM nanolines WHERE id = ?", [nanoline_id])

        if not nanoline:
            return "Could not find nanoline with ID <highlight>%d<end>." % nanoline_id

        data = self.db.query("SELECT n1.lowid, n1.lowql, n1.name, n1.location "
                             "FROM nanos n1 JOIN nanos_nanolines_ref n2 ON n1.lowid = n2.lowid "
                             "WHERE n2.nanolines_id = ? "
                             "ORDER BY n1.lowql DESC, n1.name ASC", [nanoline_id])

        blob = ""
        for row in data:
            blob += "%s [%d] %s\n" % (self.text.make_item(row.lowid, row.lowid, row.lowql, row.name), row.lowql, row.location)
        blob += self.get_footer()

        return ChatBlob("%s %s Nanos" % (nanoline.profession, nanoline.name), blob)

    @command(command="nanolines", params=[Any("profession")], access_level="all",
             description="Show nanolines by profession")
    def nanolines_profession_cmd(self, channel, sender, reply, args):
        prof_name = args[0]

        profession = self.util.get_profession(prof_name)
        if not profession:
            return "Could not find profession <highlight>%s<end>." % prof_name

        data = self.db.query("SELECT * FROM nanolines WHERE profession = ? ORDER BY name ASC", [profession])

        blob = ""
        for row in data:
            blob += self.text.make_chatcmd(row.name, "/tell <myname> nanolines %d" % row.id) + "\n"
        blob += self.get_footer()

        return ChatBlob("%s Nanolines" % profession, blob)

    def get_footer(self):
        return "\n\nNanos DB provided by Saavick & Lucier"