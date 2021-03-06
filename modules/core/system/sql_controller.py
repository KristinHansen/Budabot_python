from core.decorators import instance, command
from core.command_param_types import Any, Const
from core.chat_blob import ChatBlob
import json


@instance()
class SqlController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")

    @command(command="sql", params=[Const("query"), Any("sql_statement")], access_level="superadmin",
             description="Execute a SQL query and return the results")
    def sql_query_cmd(self, request, _, sql):
        try:
            results = self.db.query(sql)
            return ChatBlob("Results (%d)" % len(results), json.dumps(results, indent=4, sort_keys=True))
        except Exception as e:
            return "There was an error executing your query: %s" % str(e)

    @command(command="sql", params=[Const("exec"), Any("sql_statement")], access_level="superadmin",
             description="Execute a SQL query and return number of affected rows")
    def sql_exec_cmd(self, request, _, sql):
        try:
            row_count = self.db.exec(sql)
            return "%d row(s) affected." % row_count
        except Exception as e:
            return "There was an error executing your query: %s" % str(e)
