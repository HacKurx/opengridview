import threading
from gi.repository import Gtk,Gio,Gdk
from opengridview.parser import Parser
from gi.repository import GObject
import csv
import io

class Window(Gtk.ApplicationWindow):

    def __init__(self,input_stream,input_config):
        if input_config.get('title',None):
          title = 'Open-GridView - %s' % input_stream.name
        else:
          title = 'Open-GridView'
        Gtk.Window.__init__(self, title=title)

        # Set variables
        self.input_stream = input_stream
        self.input_config = input_config
        self.should_stop = False
        self.stream_end = False
        self.tree_source = None
        self.done_headers = False

        box = Gtk.Box(orientation='vertical', spacing=5)
        self.add(box)

        self.txt_filter = Gtk.Entry()
        box.pack_start(self.txt_filter, False, True, 0)

        sw = Gtk.ScrolledWindow()
        box.pack_start(sw, True, True, 0)

        self.tree_view = Gtk.TreeView()
        self.tree_view.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        sw.add(self.tree_view)

        action_group = Gtk.ActionGroup('my_actions')
        action_group.add_actions([
                ("EditMenu", None, "Edit"),
                ("EditCopy",None,'copy','<Ctrl>c',None,self.copy_clipboard_noheaders),
                ("EditCopyHeaders",None,'Copy (with headers)','<Ctrl><Shift>c',None,self.copy_clipboard_headers)
            ])
        uimanager = Gtk.UIManager()
        uimanager.add_ui_from_string("""
            <ui>
               <menubar name='MenuBar'>
                   <menu action='EditMenu'>
                       <menuitem action='EditCopy' />
                       <menuitem action='EditCopyHeaders' />
                   </menu>
               </menubar>
           </ui>
        """)
        uimanager.insert_action_group(action_group)
        accelgroup = uimanager.get_accel_group()
        menubar = uimanager.get_widget("/MenuBar")
        box.pack_start(menubar, False, False, 0)
        self.add_accel_group(accelgroup)

        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        # Set my position
        self.connect_after('show', lambda window:
                GObject.idle_add(self.my_set_position)
                )

    def my_set_position(self):
        screen = self.get_screen()
        monitor = screen.get_monitor_at_window(self.get_window())
        geometry = screen.get_monitor_geometry(monitor)
        self.resize( geometry.width * 0.75 , geometry.height * 0.75 )

    def copy_clipboard_noheaders(self,action):
        self._copy_clipboard(False)
    def copy_clipboard_headers(self,action):
        self._copy_clipboard(True)

    # TODO Wanted to use more sophisticated data type but cant http://stackoverflow.com/q/25151437
    def _copy_clipboard(self,include_headers):
      if not self.done_headers:
          return
      res = io.StringIO()
      source,paths = self.tree_view.get_selection().get_selected_rows()
      writer = csv.writer(res)
      if include_headers:
          writer.writerow(self.headers)
      for path in paths:
        iter = source.get_iter(path)
        cells = [ source.get_value(iter,i) for i in range(0,self.tree_source.get_n_columns()) ]
        writer.writerow(cells)
      self.clipboard.set_text(res.getvalue(),-1)

    # Set headers for the table
    def set_headers(self,headers):
      header_titles,header_types = list(zip(*headers))
      if self.done_headers: return
      self.headers = header_titles
      self.header_types = header_types
      for idx, title in enumerate(header_titles):
        if not title: continue # Skip columns with empty titles
        r = Gtk.CellRendererText()
        c = Gtk.TreeViewColumn(title,r, text=idx)
        c.set_resizable(True)
        c.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        c.set_sort_column_id(idx)
        self.tree_view.append_column(c)
      # Create source
      header_types = [str if x == str else x for x in header_types]
      self.tree_source = Gtk.ListStore(*header_types)
      tree_filter = self.tree_source.filter_new()
      tree_sort = Gtk.TreeModelSort(model=tree_filter)
      self.tree_view.set_model(tree_sort)
      self.txt_filter.connect("changed", lambda x: tree_filter.refilter())
      tree_filter.set_visible_func(self.filter)
      if 'filter' in self.input_config:
        self.txt_filter.set_text(self.input_config['filter'])
      self.done_headers = True

    # Add new item
    def add_item(self,item):
      # assuming item is array of values
      z = list(zip(item,self.headers))
      if not any(((cell[0] != None) and cell[1] for cell in z)): return # Skip items that have no values in columns with names
      self.tree_source.append(item)
      if not self.get_visible():
          self.show_all()

    def filter(self,obj,iteration,b):
      filter_text = self.txt_filter.get_text()
      # simple filter
      for i in range(0,len(self.headers)):
        if filter_text in str(obj.get_value(iteration,i)): return True
      return False

    def start_read(self):
      th = threading.Thread(target=self.read_stream)
      th.daemon=True
      th.start()

    def read_stream(self):
      parser = Parser.find_parser(self.input_config)
      parser.read_stream(
              self.input_stream,
              lambda item: GObject.idle_add(self.add_item, item),
              lambda headers: GObject.idle_add(self.set_headers,headers)
              )
