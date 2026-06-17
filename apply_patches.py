#!/usr/bin/env python3
"""Apply all patches to aRDP v6.4.2 source code."""
import os, re

BASE = os.path.dirname(os.path.abspath(__file__))

def read(path):
    with open(os.path.join(BASE, path), 'r', encoding='utf-8') as f:
        return f.read()

def write(path, content):
    with open(os.path.join(BASE, path), 'w', encoding='utf-8') as f:
        f.write(content)

patches_applied = 0

# ============================================================
# Patch 1: RemoteRdpKeyboard.java - Add instance, keyboardActive, sendKeyEvent
# ============================================================
print("Patching RemoteRdpKeyboard.java...")
f = 'bVNC/src/main/java/com/iiordanov/bVNC/input/RemoteRdpKeyboard.java'
c = read(f)

# Add static instance field and keyboardActive field after class declaration
old_class = '''public class RemoteRdpKeyboard extends RemoteKeyboard {
    private final static String TAG = "RemoteRdpKeyboard";
    protected RdpKeyboardMapper keyboardMapper;
    protected Viewable canvas;
    protected InputCarriable remoteInput;
    private RdpCommunicator rdpcomm;'''

new_class = '''public class RemoteRdpKeyboard extends RemoteKeyboard {
    private final static String TAG = "RemoteRdpKeyboard";

    // Static instance reference for AccessibilityService to access
    public static volatile RemoteRdpKeyboard instance = null;
    // Whether keyboard is active and should receive events
    public volatile boolean keyboardActive = false;

    protected RdpKeyboardMapper keyboardMapper;
    protected Viewable canvas;
    protected InputCarriable remoteInput;
    private RdpCommunicator rdpcomm;'''

c = c.replace(old_class, new_class)

# Add sendKeyEvent method and set instance in constructor
old_ctor_end = '''        keyboardMapper.init(context);
        keyboardMapper.reset((RdpKeyboardMapper.KeyProcessingListener) r);
    }'''

new_ctor_end = '''        keyboardMapper.init(context);
        keyboardMapper.reset((RdpKeyboardMapper.KeyProcessingListener) r);
        instance = this;
        keyboardActive = true;
    }

    /**
     * Send a key event from AccessibilityService.
     * @param e the KeyEvent from accessibility service
     * @param down true if key down, false if key up
     */
    public void sendKeyEvent(android.view.KeyEvent e, boolean down) {
        if (rdpcomm != null && rdpcomm.isInNormalProtocol()) {
            int keyCode = e.getKeyCode();
            int metaState = convertEventMetaState(e) | onScreenMetaState;
            rdpcomm.writeKeyEvent(keyCode, metaState, down);
            // Also process through keyboard mapper for complex keys
            if (down) {
                keyboardMapper.processAndroidKeyEvent(e, false);
            }
        }
    }'''

c = c.replace(old_ctor_end, new_ctor_end)
write(f, c)
patches_applied += 1
print("  OK")

# ============================================================
# Patch 2: RemoteCanvasActivity.java - Multiple changes
# ============================================================
print("Patching RemoteCanvasActivity.java...")
f = 'bVNC/src/main/java/com/iiordanov/bVNC/RemoteCanvasActivity.java'
c = read(f)

# 2a: Add Toast import
c = c.replace(
    'import android.widget.ListView;',
    'import android.widget.ListView;\nimport android.widget.Toast;'
)

# 2b: Add hasForegroundInstance static field and toolbarPermanentlyHidden field
c = c.replace(
    'public class RemoteCanvasActivity extends AppCompatActivity implements\n'
    '        SelectTextElementFragment.OnFragmentDismissedListener, TouchInputDelegate {\n',
    'public class RemoteCanvasActivity extends AppCompatActivity implements\n'
    '        SelectTextElementFragment.OnFragmentDismissedListener, TouchInputDelegate {\n\n'
    '    // Static flag for AccessibilityService to check if a RemoteCanvas is in foreground\n'
    '    public static volatile boolean hasForegroundInstance = false;\n'
    '    // Whether the toolbar has been permanently hidden by the user\n'
    '    private boolean toolbarPermanentlyHidden = false;\n'
)

# 2c: Set hasForegroundInstance in onResume
c = c.replace(
    '    protected void onResume() {\n'
    '        super.onResume();\n'
    '        Log.i(TAG, "onResume called.");',
    '    protected void onResume() {\n'
    '        super.onResume();\n'
    '        hasForegroundInstance = true;\n'
    '        Log.i(TAG, "onResume called.");'
)

# 2d: Clear hasForegroundInstance in onPause
c = c.replace(
    '    protected void onPause() {\n'
    '        super.onPause();\n'
    '        Log.i(TAG, "onPause called.");',
    '    protected void onPause() {\n'
    '        super.onPause();\n'
    '        hasForegroundInstance = false;\n'
    '        Log.i(TAG, "onPause called.");'
)

# 2e: Clear hasForegroundInstance and instance in onDestroy
c = c.replace(
    '    protected void onDestroy() {\n'
    '        super.onDestroy();\n'
    '        Log.i(TAG, "onDestroy called.");\n'
    '        if (remoteConnection != null)\n'
    '            remoteConnection.closeConnection();\n'
    '        System.gc();\n'
    '    }',
    '    protected void onDestroy() {\n'
    '        super.onDestroy();\n'
    '        hasForegroundInstance = false;\n'
    '        com.iiordanov.bVNC.input.RemoteRdpKeyboard.instance = null;\n'
    '        Log.i(TAG, "onDestroy called.");\n'
    '        if (remoteConnection != null)\n'
    '            remoteConnection.closeConnection();\n'
    '        System.gc();\n'
    '    }'
)

# 2f: Add guard to showActionBar()
c = c.replace(
    '    public void showActionBar() {\n'
    '        handler.removeCallbacks(actionBarShower);',
    '    public void showActionBar() {\n'
    '        if (toolbarPermanentlyHidden) return;\n'
    '        handler.removeCallbacks(actionBarShower);'
)

# 2g: Add itemHideToolbar menu handler before the else block
old_menu = '''        } else {
            boolean inputModeSet = setInputMode(item.getItemId());
            item.setChecked(inputModeSet);
            if (inputModeSet) {
                return true;
            }
        }
        return super.onOptionsItemSelected(item);'''

new_menu = '''        } else if (itemId == R.id.itemHideToolbar) {
            toolbarPermanentlyHidden = !toolbarPermanentlyHidden;
            if (toolbarPermanentlyHidden) {
                item.setTitle(R.string.show_toolbar);
                handler.removeCallbacks(actionBarShower);
                Objects.requireNonNull(getSupportActionBar()).hide();
                Toast.makeText(this, R.string.toolbar_hidden_toast, Toast.LENGTH_LONG).show();
            } else {
                item.setTitle(R.string.hide_toolbar);
                showActionBar();
            }
            return true;
        } else {
            boolean inputModeSet = setInputMode(item.getItemId());
            item.setChecked(inputModeSet);
            if (inputModeSet) {
                return true;
            }
        }
        return super.onOptionsItemSelected(item);'''

c = c.replace(old_menu, new_menu)
write(f, c)
patches_applied += 1
print("  OK")

# ============================================================
# Patch 3: strings.xml (English) - Add strings
# ============================================================
print("Patching strings.xml (en)...")
f = 'bVNC/src/main/res/values/strings.xml'
c = read(f)

c = c.replace(
    '    <string name="hide_toolbar">Hide toolbar</string>',
    '    <string name="hide_toolbar">Hide toolbar</string>\n'
    '    <string name="show_toolbar">Show toolbar</string>\n'
    '    <string name="toolbar_hidden_toast">Toolbar hidden. Reconnect to restore.</string>\n'
    '    <string name="keyboard_accessibility_service_description">Captures physical keyboard events (including Meta/Win key) and sends them to the remote desktop session.</string>'
)
write(f, c)
patches_applied += 1
print("  OK")

# ============================================================
# Patch 4: strings.xml (Chinese) - Add strings
# ============================================================
print("Patching strings.xml (zh)...")
f = 'bVNC/src/main/res/values-zh-rCN/strings.xml'
c = read(f)

c = c.replace(
    '    <string name="hide_toolbar">隐藏工具栏</string>',
    '    <string name="hide_toolbar">隐藏工具栏</string>\n'
    '    <string name="show_toolbar">显示工具栏</string>\n'
    '    <string name="toolbar_hidden_toast">工具栏已隐藏，重新连接可恢复。</string>\n'
    '    <string name="keyboard_accessibility_service_description">捕获物理键盘事件（包括 Meta/Win 键）并发送到远程桌面会话。</string>'
)
write(f, c)
patches_applied += 1
print("  OK")

# ============================================================
# Patch 5: canvasactivitymenu.xml - Add menu item
# ============================================================
print("Patching canvasactivitymenu.xml...")
f = 'bVNC/src/main/res/menu/canvasactivitymenu.xml'
c = read(f)

# Add itemHideToolbar before itemDisconnect
if 'itemDisconnect' in c:
    c = c.replace(
        'itemDisconnect',
        'itemHideToolbar" android:title="@string/hide_toolbar" />\n    <item android:id="@+id/itemDisconnect'
    )
    # Fix: the replace above is a bit hacky, let's be more precise
    # Revert and do it properly
    c = c.replace(
        'itemHideToolbar" android:title="@string/hide_toolbar" />\n    <item android:id="@+id/itemDisconnect',
        ''
    )
    # Find the itemDisconnect item and add before it
    import re as re2
    pattern = r'(<item[^>]*itemDisconnect[^>]*/?>)'
    match = re2.search(pattern, c)
    if match:
        insert_before = match.group(0)
        new_item = '<item android:id="@+id/itemHideToolbar" android:title="@string/hide_toolbar" />\n    ' + insert_before
        c = c.replace(insert_before, new_item, 1)
        write(f, c)
        patches_applied += 1
        print("  OK")
    else:
        print("  WARNING: Could not find itemDisconnect pattern, trying alternate")
        # Try to find by looking at the raw content
        lines = c.split('\n')
        new_lines = []
        inserted = False
        for line in lines:
            if 'itemDisconnect' in line and not inserted:
                new_lines.append('    <item android:id="@+id/itemHideToolbar" android:title="@string/hide_toolbar" />')
                inserted = True
            new_lines.append(line)
        c = '\n'.join(new_lines)
        write(f, c)
        patches_applied += 1
        print("  OK (alternate method)")
else:
    print("  WARNING: itemDisconnect not found in menu xml")

# ============================================================
# Patch 6: AndroidManifest.xml - Register accessibility service
# ============================================================
print("Patching AndroidManifest.xml...")
f = 'aRDP-app/src/main/AndroidManifest.xml'
c = read(f)

service_xml = (
    '        <service android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"\n'
    '            android:name="com.iiordanov.util.KeyboardAccessibilityService"\n'
    '            android:label="aRDP Physical Keyboard Service"\n'
    '            android:enabled="true"\n'
    '            android:exported="false">\n'
    '            <intent-filter>\n'
    '                <action android:name="android.accessibilityservice.AccessibilityService" />\n'
    '            </intent-filter>\n'
    '            <meta-data\n'
    '                android:name="android.accessibilityservice"\n'
    '                android:resource="@xml/keyboard_accessibility_service" />\n'
    '        </service>\n'
    '    </application>'
)

c = c.replace('    </application>', service_xml)
write(f, c)
patches_applied += 1
print("  OK")

print(f"\nAll {patches_applied} patches applied successfully!")
