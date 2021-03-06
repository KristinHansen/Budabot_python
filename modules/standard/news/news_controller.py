from core.decorators import instance, command, setting, event
from core.command_param_types import Int, Const, Any
from core.setting_types import NumberSettingType, BooleanSettingType, ColorSettingType
from core.setting_service import SettingService
from core.lookup.character_service import CharacterService
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.util import Util
from core.logger import Logger
from core.command_param_types import Int, Any, Regex
from core.private_channel_service import PrivateChannelService
from modules.core.org_members.org_member_controller import OrgMemberController
import time

@instance()
class NewsController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.util: Util = registry.get_instance("util")

    @setting(name="number_news_shown", value="10", description="Maximum number of news items shown")
    def number_news_shown(self):
        return NumberSettingType()

    @setting(name="include_read_on_logon", value="False", description="Include read news when player logs on")
    def include_read_on_logon(self):
        return BooleanSettingType()

    @setting(name="unread_color", value="#ffff00", description="Color for unread news text")
    def unread_color(self):
        return ColorSettingType()

    @setting(name="sticky_color", value="#ffff00", description="Color for sticky news text")
    def sticky_color(self):
        return ColorSettingType()

    @setting(name="news_color", value="#ffffff", description="Color for news text")
    def news_color(self):
        return ColorSettingType()

    def build_news_list(self, include_read=True, char_id=None):
        blob = ""

        if not include_read and char_id is not None:
            blob += self.get_unread_news(char_id)
        else:
            stickies = self.get_sticky_news()
            news = self.get_news()

            blob += "<header2>Stickies<end>\n"
            blob += "No stickies\n" if stickies is None else stickies
            blob += "____________________________\n\n"
            blob += "No news" if news is None else news

        return blob if len(blob) > 0 else None

    def has_unread_news(self, char_id):
        sql = "SELECT COUNT(*) as count FROM news n WHERE n.news_id NOT IN ( SELECT r.news_id FROM news_read r WHERE r.char_id = ? ) AND n.deleted = 0"
        news_unread_count = self.db.query_single(sql, [char_id]).count

        if news_unread_count < 1:
            sql = "SELECT COUNT(*) as count FROM news n WHERE n.deleted = 0"
            news_count = self.db.query_single(sql).count

            if news_count < 1:
                return None

        return (news_unread_count > 0)

    def get_unread_news(self, char_id):
        number_news_shown = self.setting_service.get("number_news_shown").get_value()
        sql = "SELECT * FROM news n WHERE n.news_id NOT IN ( SELECT r.news_id FROM news_read r WHERE char_id = ? ) AND n.deleted = 0 ORDER BY n.sticky DESC, n.time DESC LIMIT ?"
        news = self.db.query(sql, [char_id, number_news_shown])

        blob = ""

        if news:
            more_stickies = True
            for item in news:
                if item.sticky == 0 and more_stickies:
                    if len(blob) <= 0:
                        blob += "No stickies\n"
                    blob += "____________________________\n\n"
                    more_stickies = False

                unread_color = self.setting_service.get("unread_color").get_font_color()
                remove_link = self.text.make_chatcmd("Remove", "/tell <myname> news rem %s" % (item.news_id))
                sticky_text = "Sticky" if item.sticky == 0 else "Unsticky"
                sticky_link = self.text.make_chatcmd(sticky_text, "/tell <myname> news %s %s" % (sticky_text.lower(), item.news_id))
                read_link = self.text.make_chatcmd("Mark as read", "/tell <myname> news markasread %s" % (item.news_id))
                timestamp = time.strftime("%d-%m-%Y %H:%M:%S", time.gmtime(item.time))

                blob += "%s%s<end>\n" % (unread_color, item.news)
                blob += "By %s [%s UTC] [%s] [%s] [%s]\n\n" % (item.author, timestamp, remove_link, sticky_link, read_link)
            
            if more_stickies:
                blob += "____________________________\n\n"
                blob += "No news"
                
            return blob
        
        return None

    def get_sticky_news(self):
        sql = "SELECT * FROM news n WHERE n.deleted = 0 AND n.sticky = 1 ORDER BY n.time DESC"
        news = self.db.query(sql)

        blob = ""

        if news:
            for item in news:
                stickycolor = self.setting_service.get("sticky_color").get_font_color()
                remove_link = self.text.make_chatcmd("Remove", "/tell <myname> news rem %s" % (item.news_id))
                sticky_link = self.text.make_chatcmd("Unsticky", "/tell <myname> news unsticky %s" % (item.news_id))
                timestamp = time.strftime("%d-%m-%Y %H:%M:%S", time.gmtime(item.time))

                blob += "%s%s<end>\n" % (stickycolor, item.news)
                blob += "By %s [%s UTC] [%s] [%s]\n\n" % (item.author, timestamp, remove_link, sticky_link)

            return blob

        return None

    def get_news(self):
        number_news_shown = self.setting_service.get("number_news_shown").get_value()
        sql = "SELECT * FROM news n WHERE n.deleted = 0 AND n.sticky = 0 ORDER BY n.time DESC LIMIT ?"
        news = self.db.query(sql, [number_news_shown])

        blob = ""

        if news:
            for item in news:
                news_color = self.setting_service.get("news_color").get_font_color()
                remove_link = self.text.make_chatcmd("Remove", "/tell <myname> news rem %s" % (item.news_id))
                sticky_link = self.text.make_chatcmd("Sticky", "/tell <myname> news sticky %s" % (item.news_id))
                timestamp = time.strftime("%d-%m-%Y %H:%M:%S", time.gmtime(item.time))

                blob += "%s%s<end>\n" % (news_color, item.news)
                blob += "By %s [%s UTC] [%s] [%s]\n\n" % (item.author, timestamp, remove_link, sticky_link)
            
            return blob

        return None

    @command(command="news", params=[], description="Show list of news", access_level="member")
    def news_cmd(self, request):
        sql = "SELECT n.time FROM news n WHERE n.deleted = 0 ORDER BY n.time DESC LIMIT 1"
        timestamp = time.strftime("%d-%m-%Y %H:%M:%S", time.gmtime(self.db.query_single(sql).time))
        return ChatBlob("News [Last updated at %s UTC]" % (timestamp), self.build_news_list())
    
    @command(command="news", params=[Const("add"), Any("news")], description="Add news entry", access_level="moderator")
    def news_add_cmd(self, request, _, news):
        sql = "INSERT INTO news (time, author, news, sticky, deleted) VALUES (?,?,?,?,?)"
        success = self.db.exec(sql, [int(time.time()), request.sender.name, news, 0, 0])

        if success > 0:
            return "Successfully added news entry"
        else:
            return "Failed to add news entry"

    @command(command="news", params=[Const("rem"), Int("news_id")], description="Remove a news entry", access_level="moderator")
    def news_rem_cmd(self, request, _, news_id):
        sql = "DELETE FROM news WHERE news_id = ?"
        success = self.db.exec(sql, [news_id])

        if success > 0:
            return "Successfully deleted news entry with id %d" % (news_id)
        else:
            return "Failed to delete news entry with id %d, maybe id is wrong?" % (news_id)

    @command(command="news", params=[Const("sticky"), Int("news_id")], description="Sticky a news entry", access_level="moderator")
    def news_sticky_cmd(self, request, _, news_id):
        sql = "UPDATE news SET sticky = 1 WHERE news_id = ?"
        success = self.db.exec(sql, [news_id])

        if success > 0:
            return "Successfully updated news entry with id %d to a sticky" % (news_id)
        else:
            return "Failed to update news entry with id %d, maybe id is wrong?" % (news_id)

    @command(command="news", params=[Const("unsticky"), Int("news_id")], description="Unsticky a news entry", access_level="moderator")
    def news_unsticky_cmd(self, request, _, news_id):
        sql = "UPDATE news SET sticky = 0 WHERE news_id = ?"
        success = self.db.exec(sql, [news_id])

        if success > 0:
            return "Successfully removed news entry with id %d as a sticky" % (news_id)
        else:
            return "Failed to update news entry with id %d, maybe id is wrong?" % (news_id)

    @command(command="news", params=[Const("markasread"), Int("news_id")], description="Mark a news entry as read", access_level="member")
    def news_markasread_cmd(self, request, _, news_id):
        sql = "INSERT INTO news_read (char_id, news_id) VALUES (?,?)"
        success = self.db.exec(sql, [request.sender.char_id, news_id])

        if success > 0:
            return "Successfully marked news entry with id %d as read" % (news_id)
        else:
            return "Failed to mark news entry with id %d as read, maybe id is wrong?" % (news_id)
    
    @event(OrgMemberController.ORG_MEMBER_LOGON_EVENT, "Send news list when org member logs on")
    def orgmember_logon_event(self, event_type, event_data):
        include_read = self.setting_service.get("include_read_on_logon").get_value()
        unread_news = self.has_unread_news(event_data.char_id)

        if not include_read and unread_news is None:
            # No news at all
            return
        elif not include_read and not unread_news:
            # No new unread entries
            return

        news = self.build_news_list(False, event_data.char_id) if not include_read else self.build_news_list()
        
        if news:
            self.bot.send_private_message(event_data.char_id, ChatBlob("News", news))

    @event(PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, "Send news list when someone joins private channel")    
    def priv_logon_event(self, event_type, event_data):
        include_read = self.setting_service.get("include_read_on_logon").get_value()
        unread_news = self.has_unread_news(event_data.char_id)

        if not include_read and unread_news is None:
            # No news at all
            return
        elif not include_read and not unread_news:
            # No new unread entries
            return
        
        news = self.build_news_list(False, event_data.char_id) if not include_read else self.build_news_list()
        
        if news:
            self.bot.send_private_message(event_data.char_id, ChatBlob("News", news))