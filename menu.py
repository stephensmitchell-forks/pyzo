
import os, sys, re, time
import unicodedata

from PyQt4 import QtCore, QtGui
from PyQt4 import Qsci
qt = QtGui

import iep
from iepLogging import print

class MI:
    """ Menu Item
    A virtual menu item to help producing a menu. 
    It can represent:
    - an action - values is None
    - a boolean - values is True or False, indicating the currents state
    - a choice - values is a list of Strings, ending with the current
    
    - if doc not given, func.__doc__ is used as 3ti
    - if values is [], func(None) is called to obtain the 'values' property.
    """
    def __init__(self, text, func, values=None, doc=None):        
        # Get text and func (always directly)
        self.text = text
        self.func = func
        # Get doc
        if doc is None:
            self.tip = func.__doc__
        else:
            self.tip = doc
        # Get values
        if values is None:
            self.values = None
        elif values == []:
            self.values = func(None)
        else:
            self.values = values
    
    def _attachShortcut(self, action):
        # set shortcut?
        shortcuts = getShortcut(action)
        tmp = []
        for shortcut in shortcuts:
            shortcut = shortcut.replace(' ','')
            if shortcut:
                tmp.append(shortcut)
        if not tmp:
            return
        # attach
        action.setShortcuts(tmp)
    
    
    def createRealMenuItem(self, menu):
        """ From this virtual menu item, create the actual menu
        stuff to show to the user. """
        
        # depending on type ....
        if self.values is None:
            action = qt.QAction(menu)
            action.func = self.func
            action.value = True
            action.setText(self.text)
            self._attachShortcut(action)
        elif self.values in [True, False, 0, 1]:
            action = qt.QAction(menu)
            action.func = self.func
            action.value = not self.values
            action.setCheckable(True)
            action.setChecked(self.values)
            action.setText(self.text)
            self._attachShortcut(action)
        elif isinstance(self.values, list):
            action = qt.QMenu(menu)
            action.setTitle(self.text)
            for value in self.values[:-1]:
                sub = qt.QAction(action)
                sub.setText(str(value))
                sub.setStatusTip(self.tip)
                sub.setToolTip(self.tip)
                sub.func = self.func
                sub.value = value
                sub.setCheckable(True)
                self._attachShortcut(sub)
                if value == self.values[-1]:
                    sub.setChecked(True)
                action.addAction(sub)
        else:
            print(self.values)
            raise Exception('Dont know what to do')
        
        action.setStatusTip(self.tip)
        #action.setToolTip(self.tip)
        return action


class BaseMenu(qt.QMenu):
    """ Base class for the menus File, Edit, Settings, etc. """
    
    def __init__(self, menuname, parent):
        QtGui.QMenu.__init__(self, menuname, parent)
        
        # keep a list at the menubar. We could use weakrefs, but the
        # menu's in the menubar are never destroyed, so don't bother
        if isinstance(parent, QtGui.QMenuBar):
            if not hasattr(parent, '_menus'):
                parent._menus = []
            parent._menus.append(self)
    
    def showEvent(self, event):
        """ Called right before menu is shown. The menu should update
        its contents before actually showing. """
        
        # insert items to show
        self.fill()
        
        # call base show callback
        qt.QMenu.showEvent(self, event)
    
    def addItem(self, item):
        """ Add a MI instance. """
        
        # produce real menu items
        if isinstance(item, MI):
            realitem = item.createRealMenuItem(self)
        else:
            realitem = None
        # append
        if isinstance(realitem, qt.QMenu):
            self.addMenu(realitem)
        elif isinstance(realitem, qt.QAction):
            self.addAction(realitem)
        else:
            self.addSeparator()
        # done
        return realitem
    
    def fill(self):
        """ Update the contents. """
        # clear first
        self.clear()
    

class FileMenu(BaseMenu):
    def fill(self):
        BaseMenu.fill(self)
        addItem = self.addItem
        
        addItem( MI('New file', self.fun_new) )
        addItem( MI('Open file', self.fun_open) )
        addItem( MI('Save file', self.fun_save) )
        addItem( MI('Save file as ...', self.fun_saveAs) )
        addItem( MI('Close file', self.fun_closeFile) )
        addItem(None)
        addItem( MI('Style', self.fun_style, []) )
        addItem( MI('Indentation', self.fun_indentation, []) )
        addItem( MI('Line endings', self.fun_lineEndings, []) )        
        addItem( MI('File encoding', self.fun_encoding, []) )
        addItem(None)        
        addItem( MI('Restart IEP', self.fun_restart) )
        addItem( MI('Close IEP', self.fun_close) )
        
        #addItem( MI('TEST', self.fun_test) )
    
    
    def fun_test(self, value):
        """ Test something. """
        iep.main.setWindowState(QtCore.Qt.WindowFullScreen)
        
    def fun_new(self, value):
        """ Create a new (or temporary) file. """
        iep.editors.newFile()
    
    def fun_open(self, value):
        """ Open an existing file. """
        iep.editors.openFile()
    
    def fun_save(self, value):
        """ Save the current file. """
        iep.editors.saveFile()
    
    def fun_saveAs(self, value):
        """ Save the current file under another name. """
        iep.editors.saveFileAs()
    
    def fun_closeFile(self, value):
        """ Close the current file. """
        iep.editors.closeFile()
    
    
    def fun_lineEndings(self, value):
        """ The line ending character used for the current file. """
        # get editor
        editor = iep.editors.getCurrentEditor()
        if editor is None:
            return ['no editor', '']
        
        if value is None:                        
            le = {'\n':'LF', '\r':'CR', '\r\n':'CRLF'}[editor._lineEndings]
            return ['LF', 'CR', 'CRLF', le]
        else:
            tmp = {'LF':'\n', 'CR':'\r', 'CRLF':'\r\n'}
            editor._lineEndings = tmp[value]
    
    def fun_indentation(self, value):
        """ The indentation style used for the current file. """
        # get editor
        editor = iep.editors.getCurrentEditor()
        if editor is None:
            return ['no editor', '']
        
        if value is None:
            current = editor.getIndentation()
            options = [-1,2,3,4,5,6,7,8, current]
            for i in range(len(options)):
                if options[i] < 0:
                    options[i] = 'Use tabs'
                else:
                    options[i] = '{} spaces'.format(options[i])            
            return options
        else:
            # parse value
            val = 0
            if value.lower() == 'use tabs':
                val = -1
            else:
                try:
                    val = int(value[:2])
                except ValueError:
                    pass
            # apply
            if not val:
                val = iep.config.settings.defaultIndentation
            editor.setIndentation(val)
    
    def fun_style(self, value):
        """ The styling used for the current style. """
        # get editor
        editor = iep.editors.getCurrentEditor()
        if editor is None:
            return ['no editor', '']
        
        if value is None:
            current = editor.getStyleName()
            if not current:
                current = 'default'
            options = iep.styleManager.getStyleNames()
            options.append(current)
            return options
        else:
            editor.setStyle(value)
    
    def fun_encoding(self, value):
        """ Set the encoding of the file (only UTF-8). """
        if value is None:
            return ['UTF-8', 'UTF-8']
    
    
    def fun_close(self, value):
        """ Close the application. """
        iep.main.close()
    
    
    def fun_restart(self, value):
        """ Restart the application. """
        iep.main.restart()




class EditMenu(BaseMenu):
    def fill(self):
        BaseMenu.fill(self)
        addItem = self.addItem
        
        addItem( MI('Undo', self.fun_undo) )
        addItem( MI('Redo', self.fun_redo) )
        addItem( None )
        addItem( MI('Cut', self.fun_cut) )
        addItem( MI('Copy', self.fun_copy) )
        addItem( MI('Paste', self.fun_paste) )
        addItem( MI('Select all', self.fun_selectAll) )
        addItem( None )
        addItem( MI('Comment lines', self.fun_comment) )
        addItem( MI('Uncomment lines', self.fun_uncomment) )
        addItem( None )
        addItem( MI('Move to matching brace', self.fun_moveToMatchingBrace))
        addItem( None )
        addItem( MI('Find or replace', self.fun_findReplace) )
        addItem( MI('Find selection', self.fun_findSelection) )
        addItem( MI('Find selection backward', self.fun_findSelectionBw) )
        addItem( MI('Find next', self.fun_findNext) )
        addItem( MI('Find previous', self.fun_findPrevious) )
    
    
    
    def fun_cut(self, value):
        """ Cut the text/object. """
        widget = QtGui.qApp.focusWidget()
        if hasattr(widget,'cut'):
            widget.cut()
        
    def fun_copy(self, value):
        """ Copy the text/object. """
        widget = QtGui.qApp.focusWidget()
        if hasattr(widget,'copy'):
            widget.copy()
    
    def fun_paste(self, value):
        """ Paste the text/object. """
        widget = QtGui.qApp.focusWidget()
        if hasattr(widget,'paste'):
            widget.paste()
    
    def fun_selectAll(self, value):
        """ Select the whole text. """
        widget = QtGui.qApp.focusWidget()
        if hasattr(widget,'selectAll'):
            widget.selectAll()
    
    def fun_undo(self, value):
        """ Undo the last action. """
        widget = QtGui.qApp.focusWidget()
        if hasattr(widget,'undo'):
            widget.undo()
    
    def fun_redo(self, value):
        """ Redo the last undone action """
        widget = QtGui.qApp.focusWidget()
        if hasattr(widget,'redo'):
            widget.redo()
    
    def fun_comment(self, value):
        """ Comment the selected lines. """
        widget = QtGui.qApp.focusWidget()
        if hasattr(widget,'commentCode'):
            widget.commentCode()
    
    def fun_uncomment(self, value):
        """ Uncomment the selected lines. """
        widget = QtGui.qApp.focusWidget()
        if hasattr(widget,'uncommentCode'):
            widget.uncommentCode()
            linenr, index = widget.getLinenrAndIndex()
    
    def fun_moveToMatchingBrace(self, value):
        """ Move the cursor to the brace matching the current brace. """
        widget = QtGui.qApp.focusWidget()
        if hasattr(widget,'moveToMatchingBrace'):
            widget.moveToMatchingBrace()
    
    def fun_findReplace(self, value):
        iep.editors._findReplace.startFind()
    
    def fun_findSelection(self, value):
        iep.editors._findReplace.startFind()
        iep.editors._findReplace.findNext()
    
    def fun_findSelectionBw(self, value):
        iep.editors._findReplace.startFind()
        iep.editors._findReplace.findPrevious()
    
    def fun_findNext(self, value):
        iep.editors._findReplace.findNext()
        
    def fun_findPrevious(self, value):
        iep.editors._findReplace.findPrevious()
    



class ViewMenu(BaseMenu):
    def fill(self):
        BaseMenu.fill(self)
        addItem = self.addItem
        
        addItem( MI('Select shell', self.fun_selectShell) )
        addItem( MI('Select editor', self.fun_selectEditor) )
        addItem( MI('Select previous file', self.fun_selectPrevious) )
        addItem( None )
        addItem( MI('Show whitespace', self.fun_showWhiteSpace, []) )
        addItem( MI('Show line endings', self.fun_showLineEndings, []) )
        addItem( MI('Show wrap symbols', self.fun_showWrapSymbols, []) )
        addItem( MI('Show indentation guides', self.fun_indentGuides, []) )
        addItem( MI('Show status bar', self.fun_showStatusBar) )
        addItem( None )
        addItem( MI('Wrap long lines', self.fun_wrap, []) )
        addItem( MI('Highlight current line', self.fun_lineHighlight, []) )
        addItem( MI('Match braces', self.fun_braceMatch, []) )  
        addItem( MI('Enable code folding', self.fun_codeFolding, []) ) 
        addItem( None )
        addItem( MI('Edge column', self.fun_edgecolumn, []) )
        addItem( MI('Tab width (when using tabs)', self.fun_tabWidth, []) )
        addItem( MI('Zooming', self.fun_zooming, []) )
        addItem( MI('QT theme', self.fun_qtstyle, []) )
    
    
    def fun_selectEditor(self, value):
        """ Select the current editor. """
        editor = iep.editors.getCurrentEditor()
        if editor:
            editor.setFocus()
    
    def fun_selectShell(self, value):
        """ Select the current shell. """
        shell = iep.shells.getCurrentShell()
        if shell:
            shell.setFocus()
    
    
    def fun_showStatusBar(self, value):
        """ Display the status bar atthe bottom of the window. """ 
        if value is None:
            return bool(iep.config.view.showStatusbar)
        value = not bool( iep.config.view.showStatusbar ) 
        iep.config.view.showStatusbar = value
        if value:
            iep.status = iep.main.statusBar()
        else:
            iep.status = None
            iep.main.setStatusBar(None)
    
    def fun_wrap(self, value):
        """ Wrap long lines. """
        if value is None:
            return bool(iep.config.view.wrapText)
        value = not bool( iep.config.view.wrapText ) 
        iep.config.view.wrapText = value
        for editor in iep.editors:
            editor.setWrapMode(int(value)*2)
    
    def fun_braceMatch(self, value):
        """ Indicate matching braces and when no matching brace is found. """
        if value is None:
            return bool(iep.config.view.doBraceMatch)
        else:
            # get new value
            value = not bool(iep.view.editor.doBraceMatch)
            # apply
            iep.config.view.doBraceMatch = value
            value = {True:2,False:0}[value]
            for editor in iep.editors:
                editor.SendScintilla(editor.SCI_BRACEBADLIGHT, -1) # reset
                editor.setBraceMatching(value)
            for shell in iep.shells:
                shell.SendScintilla(editor.SCI_BRACEBADLIGHT, -1) # reset
                shell.setBraceMatching(value)
    
    def fun_edgecolumn(self, value):
        """ The position of the edge column indicator. """
        if value is None:
            return [60, 65, 70, 75, 76, 77, 78,79,80,-1, 
                        iep.config.view.edgeColumn]
        iep.config.view.edgeColumn = value
        for editor in iep.editors:
            editor.setEdgeColumn(value)
    
    def fun_indentGuides(self, value):
        """ Show vertical lines at each indentation level. """
        if value is None:
            return bool(iep.config.view.showIndentGuides)
        else:
            value = not bool( iep.config.view.showIndentGuides ) 
            iep.config.view.showIndentGuides = value
            for editor in iep.editors:
                editor.setIndentationGuides(value)
    
    def fun_showWhiteSpace(self, value):
        """ Show tabs and spaces in the editor. """
        if value is None:
            return bool(iep.config.view.showWhiteSpace)
        # for the sortcuts to work
        value = not bool( iep.config.view.showWhiteSpace ) 
        # apply
        iep.config.view.showWhiteSpace = value
        for editor in iep.editors:
            editor.setViewWhiteSpace(value)
    
    def fun_showLineEndings(self, value):
        """ Show line endings in the editor. """
        if value is None:
            return bool(iep.config.view.showLineEndings)
        # for the sortcuts to work
        value = not bool( iep.config.view.showLineEndings ) 
        # apply
        iep.config.view.showLineEndings = value
        for editor in iep.editors:
            editor.setViewEOL(value)
    
    def fun_showWrapSymbols(self, value):
        """ Show wrap symbols in the editor. """
        if value is None:
            return bool(iep.config.view.showWrapSymbols)
        # for the sortcuts to work
        value = not bool( iep.config.view.showWrapSymbols ) 
        # apply
        iep.config.view.showWrapSymbols = value
        for editor in iep.editors:
            editor.setViewWrapSymbols(int(value)*1)
    
    def fun_tabWidth(self, value):
        """ The amount of space of a tab (but only if tabs are used). """
        if value is None:
            return [2,3,4,5,6,7,8,9,10, iep.config.view.tabWidth]
        
        # store and apply
        iep.config.view.tabWidth = value
        for editor in iep.editors:
            editor.setTabWidth(value)
    
    def fun_selectPrevious(self, value):
       iep.editors._list.selectPreviousItem() 
    
    def fun_zooming(self, value):
        """ Zoom in or out, or reset zooming. """
        if value is None:
            return ["Zoom in", "Zoom out", 'Zoom reset', 'this wont match']
        else:
            if "in" in value:
                iep.config.view.zoom += 1
            elif "out" in value:
                iep.config.view.zoom -= 1
            else:
                iep.config.view.zoom = 0
            iep.styleManager.styleUpdate.emit()
    
    def fun_lineHighlight(self, value):
        """ Whether the line containing the cursor should be highlighted. """
        if value is None:
            return bool(iep.config.view.highlightCurrentLine)
        else:
            value = not bool(iep.view.editor.highlightCurrentLine)
            iep.config.view.highlightCurrentLine = value
            for editor in iep.editors:
                editor.setHighlightCurrentLine(value)
    
    def fun_codeFolding(self, value):
        """ Enable folding (hiding) pieces of code. """
        if value is None:
            return bool(iep.config.view.codeFolding)
        else:
            value = not iep.config.view.codeFolding
            iep.config.view.codeFolding = value
            scin = Qsci.QsciScintilla
            tmp = {False:scin.NoFoldStyle, True:scin.BoxedTreeFoldStyle}[value]
            for editor in iep.editors:                
                editor.setFolding(tmp)

    def fun_qtstyle(self, value):
        """ Chose the QT style to use. """
        if value is None:
            # Create list of styles
            styleNames = [i for i in QtGui.QStyleFactory.keys()]
            styleNames.append(iep.config.view.qtstyle)
            # Mark the default
            for i in range(len(styleNames)):
                if styleNames[i].lower() == iep.defaultQtStyleName:
                    styleNames[i] += ' (default)'
            return styleNames
        else:
            # Remove default string
            value = value.split(' ')[0]
            # Store selected style
            iep.config.view.qtstyle = value
            # Set style and apply standard pallette
            qstyle = QtGui.qApp.setStyle(value)
            if qstyle:
                QtGui.qApp.setPalette(QtGui.QStyle.standardPalette(qstyle))


class SettingsMenu(BaseMenu):
    def fill(self):
        BaseMenu.fill(self)
        addItem = self.addItem
        
        addItem( MI('Automatically indent', self.fun_autoIndent, []) )        
        addItem( MI('Enable call tips', self.fun_callTip, []) )
        addItem( MI('Enable auto completion', self.fun_autoComplete, []) )
        addItem( MI('Autocomplete keywords', self.fun_autoComplete_kw, []) )
        addItem( None )
        addItem( MI('Default style', self.fun_defaultStyle, []) )
        addItem( MI('Default indentation', self.fun_defaultIndentation, []) )
        addItem( MI('Default line endings', self.fun_defaultLineEndings, []) )
        addItem( None )
        addItem( MI('Change key mappings ...', self.fun_keymap) )
        addItem( MI('Edit syntax styles ...', self.fun_editStyles) )
        addItem( MI('Advanced settings ...', self.fun_advancedSettings) )
        #addItem( MI('Save settings now', self.fun_saveSettings) )
        
    
    def fun_defaultStyle(self, value):
        """ The style used in new files. """
        if value is None:
            current = iep.config.settings.defaultStyle
            options = iep.styleManager.getStyleNames()
            options.append(current)
            return options
        else:
            # store
            iep.config.settings.defaultStyle = value
    
    def fun_defaultIndentation(self, value):
        """ The indentation used in new files and in the shells. """
        if value is None:
            current = iep.config.settings.defaultIndentation
            options = [-1,2,3,4,5,6,7,8,9,10, current]
            for i in range(len(options)):
                if options[i] < 0:
                    options[i] = 'Use tabs'
                else:
                    options[i] = '{} spaces'.format(options[i])            
            return options
        
        # parse value
        try:
            val = int(value[:2])
        except ValueError:
            val = -1        
        # store
        iep.config.settings.defaultIndentation = val
        # Apply to shells
        for shell in iep.shells:
            shell.setIndentation(val)
    
    def fun_defaultLineEndings(self, value):
        """ The line endings used in new files. """
        if value is None:
            current = iep.config.settings.defaultLineEndings
            return ['LF', 'CR', 'CRLF', current]
        else:
            # store
            iep.config.settings.defaultLineEndings = value
    
    def fun_autoComplete(self, value):
        """ Show a list with completion options queried from editor and shell."""
        if value is None:
            return bool(iep.config.settings.autoComplete)
        else:
            value = not bool(iep.config.settings.autoComplete)
            iep.config.settings.autoComplete = value
    
    def fun_autoComplete_kw(self, value):
        """ Show the keywords in the autocompletion list."""
        if value is None:
            return bool(iep.config.settings.autoComplete_keywords)
        else:
            value = not bool(iep.config.settings.autoComplete_keywords)
            iep.config.settings.autoComplete_keywords = value
    
    def fun_callTip(self, value):
        """ Show a call tip for functions and methods."""
        if value is None:
            return bool(iep.config.settings.autoCallTip)
        else:
            value = not bool(iep.settings.settings.autoCallTip)
            iep.config.settings.autoCallTip = value
    
    def fun_autoIndent(self, value):
        """ Enable auto-indentation (python style only). """
        if value is None:
            return bool(iep.config.settings.autoIndent)
        else:
            value = not bool(iep.config.settings.autoIndent)
            iep.config.settings.autoIndent = value
    
    def fun_keymap(self, value):
        """ Change the keymappings for the menu. """
        dialog = KeymappingDialog()
        dialog.exec_()
    
    def fun_editStyles(self, value):
        """ Edit the style file. """
        text = """ 
        The syntax styling can be changed by editing the style
        sheet, which will be opened after you press OK. The 
        changes will be applied as soon as you'll save the file.
        """   
        m = QtGui.QMessageBox(self)
        m.setWindowTitle("Edit syntax styling")
        m.setText(text)
        m.setIcon(m.Information)
        m.setStandardButtons(m.Ok | m.Cancel)
        m.setDefaultButton(m.Ok)
        result = m.exec_()
        if result == m.Ok:
            iep.editors.loadFile(os.path.join(iep.appDataDir,'styles.ssdf'))
    
    def fun_advancedSettings(self, value):
        """ How to edit the advanced settings. """
        text = """ 
        The menu does not show all available settings. The
        advanced settings can be changed by using the logger
        and typing "iep.config.advanced.". The autocompletion
        list will show you your options. 
        
        Note that most settings require a restart to take effect.
        """
        m = QtGui.QMessageBox(self)
        m.setWindowTitle("Advanced settings")
        m.setText(text)
        m.setIcon(m.Information)
        m.exec_()
    
    def fun_saveSettings(self, value):
        """ Iep saves the settings when exiting, but you can also save now. """
        iep.main.saveConfig()
        widget = QtGui.qApp.focusWidget()
        # set focus away and back, if the open file is config.ssdf, 
        # a file-changed message will appear
        iep.editors._findReplace._findText.setFocus()
        widget.setFocus()


# Instantiate plugin manager
import plugins
iep.pluginManager = pluginManager = plugins.PluginManager()

class PluginsMenu(BaseMenu):
    def fill(self):
        BaseMenu.fill(self)
        addItem = self.addItem
        
        addItem( MI('Reload tools', self.fun_reload) )
        addItem( None )
        
        for plugin in pluginManager.loadPluginInfo():
            addItem( MI(plugin.name, plugin.menuLauncher, 
                       bool(plugin.instance), plugin.description) )
    
    def fun_reload(self, value):
        """ Reload all plugins (intended for helping plugin development). """
        pluginManager.reloadPlugins()


class ShellMenu(BaseMenu):
    def fill(self):
        BaseMenu.fill(self)
        addItem = self.addItem
        
        # Insert entry for each configuration
        for info in iep.config.shellConfigs:
            text = 'Create shell: '+info.name
            action = addItem( MI(text, self.fun_create) )
            action.value = info
        
        addItem( MI('Edit shell configurations ...', self.fun_config) )
        addItem( None )
        addItem( MI('Interrupt current shell', self.fun_interrupt) )
        addItem( MI('Terminate current shell', self.fun_term) )        
        addItem( MI('Restart current shell', self.fun_restart) )        
        addItem( None )
        addItem( MI('Run selected lines', self.fun_runSelected) )
        addItem( MI('Run cell', self.fun_runCell) )
        addItem( MI('Run file', self.fun_runFile) )
        addItem( MI('Run project main file', self.fun_runProject) )
        addItem( MI('Restart shell and run project main file',  
                        self.fun_runProject2))
    
    def fun_config(self, value):
        """ Edit, add and remove configurations for the shells. """
        from shellStack import ShellInfoDialog 
        d = ShellInfoDialog()
        d.exec_()
    
    
    def fun_create(self, value):
        """ Create a new Python shell. """
        if value:
            iep.shells.addShell(value)
        else:
            iep.shells.addShell()
    
    def fun_interrupt(self, value):
        """ Send a keyboard interrupt signal to the current shell. """
        shell = iep.shells.getCurrentShell()
        if shell:
            shell.interrupt()
        
    def fun_term(self, value):
        """ Terminate (or kill if necessary) the current shell. """
        shell = iep.shells.getCurrentShell()
        if shell:
            shell.terminate()
    
    def fun_restart(self, value):
        """ Restart the current shell. """
        shell = iep.shells.getCurrentShell()
        if shell:
            shell.restart()
    
    
    def fun_runSelected(self, value):
        """ Run the selected whole lines in the current shell. """
        # Get editor and shell
        shell = iep.shells.getCurrentShell()
        editor = iep.editors.getCurrentEditor()
        if not editor or not shell:
            return        
        # Get position to sample between (only sample whole lines)
        i1, i2 = editor.getPosition(), editor.getAnchor()        
        line1 = editor.getLinenrFromPosition(i1)
        line2 = editor.getLinenrFromPosition(i2)
        line1,line2 = min(line1,line2), max(line1,line2)
        i3 = editor.getPositionFromLinenr(line1)
        i4 = editor.getPositionFromLinenr(line2+1)
        # Sample code 
        editor.setPosition(i3); editor.setAnchor(i4)
        text = editor.getSelectedString()
        # Show the result to user and set back
        editor.update()
        editor.repaint()
        time.sleep(0.200)
        editor.setPosition(i1); editor.setAnchor(i2)
        # Execute code
        fname = editor._name # or editor._filename
        shell.executeCode(text, fname, line1)
    
    def fun_runCell(self, value):
        """ Run the code between two cell separaters ('##'). """
        # Get editor and shell
        shell = iep.shells.getCurrentShell()
        editor = iep.editors.getCurrentEditor()
        if not editor or not shell:
            return 
        # Get current cell        
        i1, i2 = editor.getPosition(), editor.getAnchor()
        line1 = editor.getLinenrFromPosition(i1) # line is an int
        line2 = line1+1
        while line1>0:              
            text = editor.getLineString(line1)
            if text.startswith("##"):
                line1 +=1
                break
            else:
                line1 -=1
        maxLines = editor.getLinenrFromPosition(editor.length())
        while line2 < maxLines:
            text = editor.getLineString(line2)
            if text.startswith("##"):
                line2 -=1
                break
            else:
                line2 +=1
        else:
            line2 -=1
        # Select the text of the cell
        i3 = editor.getPositionFromLinenr(line1)
        i4 = editor.getPositionFromLinenr(line2+1)
        # Sample code 
        editor.setPosition(i3); editor.setAnchor(i4)
        text = editor.getSelectedString()
        # Show the result to user and set back
        editor.update()
        editor.repaint()
        time.sleep(0.200)
        editor.setPosition(i1); editor.setAnchor(i2)
        # Execute code
        fname = editor._name # or editor._filename
        shell.executeCode(text, fname, line1)
    
    
    def _getCodeOfFile(self, editor):
        # Obtain source code
        text = editor.getString()
        # Show the result to user and set back
        i1, i2 = editor.getPosition(), editor.getAnchor()
        editor.setPosition(0); editor.setAnchor(editor.length())
        editor.update()
        editor.repaint()
        time.sleep(0.200)
        editor.setPosition(i1); editor.setAnchor(i2)
        # Get filename and return 
        fname = editor._name # or editor._filename
        return fname, text
    
    
    def fun_runFile(self, value):
        """ Run the current file in the current shell. """
        # Get editor and shell
        shell = iep.shells.getCurrentShell()        
        editor = iep.editors.getCurrentEditor()
        if not editor or not shell:
            return        
        # Obtain source code and fname
        fname, text = self._getCodeOfFile(editor)
        # Execute
        shell.executeCode(text, fname, -1)
    
    def fun_runProject(self, value=None):
        """ Run the current project's main file. """
        # Get editor and shell
        shell = iep.shells.getCurrentShell()
        editor = iep.editors.getCurrentProjectsMainEditor()
        if not editor or not shell:
            return 
        # Run code
        fname, text = self._getCodeOfFile(editor)
        shell.executeCode(text, fname, -1)
    
    def fun_runProject2(self, value):
        """ Restart the shell and run the current project's main file. """
        shell = iep.shells.getCurrentShell()
        editor = iep.editors.getCurrentProjectsMainEditor()
        if not editor or not shell:
            return 
        # Obtain code to set as pending
        fname, text = self._getCodeOfFile(editor)
        shell.restart(text, fname, -1)
    

class HelpMenu(BaseMenu):
    def fill(self):
        BaseMenu.fill(self)
        addItem = self.addItem
        
        addItem( MI('Website', self.fun_website) )
        addItem( MI('Check for updates', self.fun_updates) )
        addItem( MI('About IEP', self.fun_about) )
    
    
    def fun_website(self, value):
        """ Open the official IEP website. """
        import webbrowser
        webbrowser.open("http://code.google.com/p/iep/")
    
    def fun_updates(self, value):
        """ Check whether a newer version of IEP is available. """
        # Get version available
        import urllib.request, re
        f = urllib.request.urlopen("http://code.google.com/p/iep/downloads/list")        
        remoteVersion = '?'
        text = str(f.read())
        for pattern in ['source.iep(.+?)\.zip', 'iep.(.+?).source\.zip']:
            result = re.search(pattern, text)
            if result:
                remoteVersion = result.group(1)
                break
        # Process
        remoteVersion = remoteVersion.strip('.').strip('_').strip()
        # Define message
        text = """ 
        Your version of IEP is: {}
        The latest version available is: {}\n        
        """.format(iep.__version__, remoteVersion)
        # Show message box
        m = QtGui.QMessageBox(self)
        m.setWindowTitle("Check for the latest version.")
        if iep.__version__ < remoteVersion:
            text += "Do you want to download the latest version?"    
            m.setStandardButtons(m.Yes | m.Cancel)
            m.setDefaultButton(m.Cancel)
        else:
            text += "Your version is up to date."    
        m.setText(text)
        m.setIcon(m.Information)
        result = m.exec_()
        # Goto webpage if user chose to
        if result == m.Yes:
            import webbrowser
            webbrowser.open("http://code.google.com/p/iep/downloads/list")
    
    
    def fun_about(self, value):
        """ Show the about text for IEP. """
        # Define icon and text
        im = QtGui.QPixmap( os.path.join(iep.iepDir,'icon48.png') ) 
        text = """ 
        IEP: the Interactive Editor for Python
        Current version: {}\n
        IEP is written in Python 3.x and uses the Qt4 widget toolkit.
        Much of its code was inspired by the Pype\n and IPython projects.\n
        IEP is subject to the General Public License (GPL)
        Copyright (C) 2010 Almar Klein
        """.format(iep.__version__)
        # Show message box
        m = QtGui.QMessageBox(self)
        m.setWindowTitle("About IEP")
        m.setText(text)
        m.setIconPixmap(im)
        m.exec_()
    

class MenuHelper:
    """ The helper class for the menus.
    It inserts the menus in the menubar.
    It catches any clicks made in the menus and makes the appropriate calls.
    """
    def __init__(self, menubar):
        
        menus = [   ('File', FileMenu), 
                    ('Edit', EditMenu), 
                    ('View', ViewMenu),                    
                    ('Settings', SettingsMenu),
                    ('Shell', ShellMenu),
                    ('Tools', PluginsMenu),
                    ('Help', HelpMenu),
                ]
        
        for menuName, menuClass in menus:
            menu = menuClass(menuName, menubar)
            menubar.addMenu(menu)
            menu.fill() # initialize so shortcuts work
        
        menubar.triggered.connect(self.onTrigger)        
        #menubar.hovered.connect(self.onHover)
    
    def onTrigger(self, action):
        if hasattr(action,'func'):
#             print('trigger:', action.text())
            action.func(action.value)
        else:
            pass # the user clicked the file, edit, menus themselves.
    
    def onHover(self, action):
        pass
        #print('hover:', action.text())
        #QtGui.QToolTip(**pos**, action.toolTip())

    

def getFullName(action):
    """ Get the full name of the action. 
    This is the key in the iep.config.shortcuts dict
    """
    item = action
    text = action.text()
    if not text:
        text = ''
    while isinstance(item.parent(), QtGui.QMenu):
        item = item.parent()
        try:
            text = item.title() + '__' + text
        except Exception:
            print('error getting name',text, item.title())
    # replace invalid chars
    text = text.replace(' ', '_')
    if text[0] in '0123456789':
        text = "_"+text
    text = re.sub('[^a-zA-z_0-9]','',text,999)
    return text.lower()


def getShortcut( fullName):
    """ Given the full name or an action, get the shortcut
    from the iep.config.shortcuts dict. A tuple is returned
    representing the two shortcuts. """
    if isinstance(fullName, QtGui.QAction):
        fullName = getFullName(fullName)
    shortcut = '', ''
    if fullName in iep.config.shortcuts:
        shortcut = iep.config.shortcuts[fullName]
        if shortcut.count(','):
            shortcut = tuple(shortcut.split(','))
        else:
            shortcut = shortcut, ''
    return shortcut

## Classes to enable editing the key mappings

class KeyMapModel(QtCore.QAbstractItemModel):
    """ The model to view the structure of the menu and the shortcuts
    currently mapped. """
    
    def __init__(self, *args):
        QtCore.QAbstractListModel.__init__(self,*args)
        self._root = None
    
    def setRootMenu(self, menu):
        """ Call this after starting. """
        menu.fill()
        self._root = menu
    
    def data(self, index, role):
        if not index.isValid() or role not in [0, 8]:
            return None
        
        # get menu or action item
        item = index.internalPointer()
        
        # get text and shortcuts
        key1, key2 = '', ''
        if isinstance(item, QtGui.QMenu):
            value = item.title()
        else:
            value = item.text()
            if not value:
                value = '-'*10
            elif index.column()>0:
                key1, key2 = '<>','<>'
                shortcuts = getShortcut(item)
                if shortcuts[0]:
                    key1 = shortcuts[0]
                if shortcuts[1]:
                    key2 = shortcuts[1]
        
        # obtain value
        value = [value,key1,key2][index.column()]
        
        # return
        if role == 0:
            # display role
            return value
        else:
            return None
#             # 8: BackgroundRole
#             brush = QtGui.QBrush(QtGui.QColor(240,255,240))
#             if value and index.column()>0:
#                 return brush
#             else:
#                 return None
            
    
    def rowCount(self, parent):
        if parent.isValid():
            menu = parent.internalPointer()
            return len(menu.actions())
        else:
            return len(self._root.actions())
    
    def columnCount(self, parent):
        return 3
    
    def headerData(self, section, orientation, role):
        if role == 0:# and orientation==1:
            tmp = ['Menu action','Shortcut 1','Shortcut 2']
            return tmp[section]
    
    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        item = index.internalPointer()
        pitem = item.parent()
        if pitem is self._root:
            return QtCore.QModelIndex()
        else:
            L = pitem.parent().actions()
            row = 0
            if pitem in L:
                row = L.index(pitem)
            return self.createIndex(row, 0, pitem)
    
    def hasChildren(self, index):
        # no items have parents (except the root item)
        
        if index.row()<0:
            return True
        else:
            return isinstance(index.internalPointer(), QtGui.QMenu)
    
    def index(self, row, column, parent):
#         if not self.hasIndex(row, column, parent):
#             return QtCore.QModelIndex()
        # establish parent
        if not parent.isValid():
            parentMenu = self._root
        else:
            parentMenu = parent.internalPointer()
        # produce index and make menu if the action represents a menu
        childAction = parentMenu.actions()[row]
        if childAction.menu():
            childAction = childAction.menu()        
        return self.createIndex(row, column, childAction)
        # This is the trick. The internal pointer is the way to establish
        # correspondence between ModelIndex and underlying data.


# Key to string mappings
k = QtCore.Qt
keymap = {k.Key_Enter:'Enter', k.Key_Return:'Return', k.Key_Escape:'Escape', 
    k.Key_Tab:'Tab', k.Key_Backspace:'Backspace', k.Key_Pause:'Pause', 
    k.Key_F1:'F1', k.Key_F2:'F2', k.Key_F3:'F3', k.Key_F4:'F4', k.Key_F5:'F5',
    k.Key_F6:'F6', k.Key_F7:'F7', k.Key_F8:'F8', k.Key_F9:'F9', 
    k.Key_F10:'F10', k.Key_F11:'F11', k.Key_F12:'F12', k.Key_Space:'Space',
    k.Key_Delete:'Delete', k.Key_Insert:'Insert', k.Key_Home:'Home', 
    k.Key_End:'End', k.Key_PageUp:'PageUp', k.Key_PageDown:'PageDown',
    k.Key_Left:'Left', k.Key_Up:'Up', k.Key_Right:'Right', k.Key_Down:'Down' }


class KeyMapLineEdit(QtGui.QLineEdit):
    """ A modified version of a lineEdit object that catches the key event
    and displays "Ctrl" when control was pressed, and similarly for alt and
    shift, function keys and other keys.
    """
    
    textUpdate = QtCore.pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        QtGui.QLineEdit.__init__(self, *args, **kwargs)
        self.setText('<enter key combination here>')
        
        # keep a list of native keys, so that we can capture for example
        # "shift+]". If we would use text(), we can only capture "shift+}"
        # which is not a valid shortcut.
        self._nativeKeys = {}
    
    def focusInEvent(self, event):
        #self.clear()
        QtGui.QLineEdit.focusInEvent(self, event)
    
    def keyPressEvent(self, event):
        
        # get key codes
        key = event.key()
        nativekey = event.nativeVirtualKey()
        
        # try to get text
        if nativekey < 128:
            text = chr(nativekey).upper()
        elif key<128:
            text = chr(key).upper()
        else:
            text = ''
        
        # do we know this specic key or this native key?
        if key in keymap:
            text = keymap[key]
        elif nativekey in self._nativeKeys:
            text = self._nativeKeys[nativekey]
        
        # apply!
        if text:
            storeNativeKey, text0 = True, text       
            if QtGui.qApp.keyboardModifiers() & k.AltModifier:
                text  = 'Alt+' + text
            if QtGui.qApp.keyboardModifiers() & k.ShiftModifier:
                text  = 'Shift+' + text
                storeNativeKey = False
            if QtGui.qApp.keyboardModifiers() & k.ControlModifier:
                text  = 'Ctrl+' + text            
            self.setText(text)
            if storeNativeKey and nativekey:
                # store native key if shift was not pressed.
                self._nativeKeys[nativekey] = text0
        
        # notify listeners
        self.textUpdate.emit()


class KeyMapEditDialog(QtGui.QDialog):
    """ The prompt that is shown when double clicking 
    a keymap in the tree. 
    It notifies the user when the entered shortcut is already used
    elsewhere and applies the shortcut (removing it elsewhere if
    required) when the apply button is pressed.
    """
    
    def __init__(self, *args):
        QtGui.QDialog.__init__(self, *args)
        
        # set title
        self.setWindowTitle('IEP - Edit shortcut mapping')
        self.setWindowIcon(iep.icon)
        
        # set size
        size = 400,140
        offset = 5
        size2 = size[0], size[1]+offset
        self.resize(*size2)
        self.setMaximumSize(*size2)
        self.setMinimumSize(*size2)
        
        self._label = QtGui.QLabel("", self)
        self._label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self._label.resize(size[0]-20, 80)
        self._label.move(10,2)
        
        self._line = KeyMapLineEdit('', self)
        self._line.resize(size[0]-80, 20)
        self._line.move(10,90)
        
        self._clear = QtGui.QPushButton("Clear", self)
        self._clear.resize(50, 20)
        self._clear.move(size[0]-60,90)
        
        self._apply = QtGui.QPushButton("Apply", self)
        self._apply.resize(50, 20)
        self._apply.move(size[0]-120,120)
        
        self._cancel = QtGui.QPushButton("Cancel", self)
        self._cancel.resize(50, 20)
        self._cancel.move(size[0]-60,120)
        
        # callbacks
        self._line.textUpdate.connect(self.onEdit)
        self._clear.clicked.connect(self.onClear)
        self._apply.clicked.connect(self.onAccept)
        self._cancel.clicked.connect(self.close)
        
        # stuff to fill in later
        self._fullname = ''
        self._intro = ''
        self._isprimary = True
        
    def setFullName(self, fullname, isprimary):
        """ To be called right after initialization to let the user
        know what he's updating, and show the current shortcut for that
        in the line edit. """
        
        # store
        self._isprimary = isprimary
        self._fullname = fullname
        # create intro to show, and store + show it
        tmp = fullname.replace('__',' -> ').replace('_', ' ')
        primSec = ['secondary', 'primary'][int(isprimary)]
        self._intro = "Set the {} shortcut for:\n{}".format(primSec,tmp)
        self._label.setText(self._intro)
        # set initial value
        if fullname in iep.config.shortcuts:
            current = iep.config.shortcuts[fullname]
            if not current.count(','):
                current += ','
            current = current.split(',')
            self._line.setText( current[int(not isprimary)] )
            
        
    def onClear(self):
        self._line.clear()
        self._line.setFocus()
    
    def onEdit(self):
        """ Test if already in use. """
        
        # init
        shortcut = self._line.text()
        if not shortcut:
            self._label.setText(self._intro)
            return
        
        for key in iep.config.shortcuts:
            # get shortcut and test whether it corresponds with what's pressed
            shortcuts = getShortcut(key)
            primSec = ''
            if shortcuts[0].lower() == shortcut.lower():
                primSec = 'primary'
            elif shortcuts[1].lower() == shortcut.lower():
                primSec = 'secondary'
            # if a correspondence, let the user know
            if primSec:
                tmp = "WARNING: combo already in use "
                tmp += "as "+primSec+" shortcut for:\n" 
                tmp += key.replace('__',' -> ').replace('_', ' ')
                self._label.setText(self._intro + '\n\n' + tmp)
                break
        else:
            self._label.setText(self._intro)
    
    
    def onAccept(self):
        shortcut = self._line.text()
        
        # remove shortcut if present elsewhere
        keys = [key for key in iep.config.shortcuts] # since it can change size
        for key in keys:
            # get shortcut and test whether it corresponds with what's pressed
            shortcuts = getShortcut(key)
            tmp = list(shortcuts)
            needUpdate = False
            if shortcuts[0].lower() == shortcut.lower():
                tmp[0] = ''
                needUpdate = True
            if shortcuts[1].lower() == shortcut.lower():
                tmp[1] = ''
                needUpdate = True
            if needUpdate:
                tmp = ','.join(tmp)
                tmp = tmp.replace(' ','')
                if len(tmp)==1:
                    del iep.config.shortcuts[key]
                else:
                    iep.config.shortcuts[key] = tmp
        
        # insert shortcut
        if self._fullname:
            # get current and make list of size two
            if self._fullname in iep.config.shortcuts:
                current = list(getShortcut(self._fullname))
            else:
                current = ['', '']
            # update the list
            current[int(not self._isprimary)] = shortcut
            iep.config.shortcuts[self._fullname] = ','.join(current)
        
        # close
        self.close()
    

class KeymappingDialog(QtGui.QDialog):
    """ The main keymap dialog, it has tabs corresponding with the
    different menus and each tab has a tree representing the structure
    of these menus. The current shortcuts are displayed. 
    On double clicking on an item, the shortcut can be edited. """
    
    def __init__(self, *args):
        QtGui.QDialog.__init__(self, *args)
        
        # set title
        self.setWindowTitle('IEP - Shortcut mappings')
        self.setWindowIcon(iep.icon)
        
        # set size
        size = 400,400
        offset = 0
        size2 = size[0], size[1]+offset
        self.resize(*size2)
        self.setMaximumSize(*size2)
        self.setMinimumSize(*   size2)
        
        self.tab = QtGui.QTabWidget(self)
        self.tab.resize(*size)
        self.tab.move(0,offset)
        
        # fill tab
        self._models = []
        self._trees = []
        for menu in iep.main.menuBar()._menus:
            # create treeview and model
            model = KeyMapModel()
            model.setRootMenu(menu)
            tree = QtGui.QTreeView(self.tab) 
            tree.setModel(model)
            # configure treeview
            tree.clicked.connect(self.onClickSelect)
            tree.doubleClicked.connect(self.onDoubleClick)
            tree.setColumnWidth(0,150)
            # append to lists
            self._models.append(model)
            self._trees.append(tree)
            self.tab.addTab(tree, menu.title())
        
        self.tab.currentChanged.connect(self.onTabSelect)

    
    def closeEvent(self, event):
        # update key setting
        for menu in iep.main.menuBar()._menus:
            menu.fill()
        event.accept()
        
    def onTabSelect(self):
        pass
        
    def onClickSelect(self, index):
        # should we show a prompt?
        item = index.internalPointer()
        if isinstance(item, QtGui.QAction) and item.text() and index.column():
            
            # create prompt dialog
            dlg = KeyMapEditDialog(self)
            fullname = getFullName(index.internalPointer())
            isprimary = index.column()==1
            dlg.setFullName( fullname, isprimary )
            # show it
            dlg.exec_()
    
    def onDoubleClick(self, index):
        pass
        