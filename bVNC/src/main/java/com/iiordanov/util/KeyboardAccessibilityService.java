package com.iiordanov.util;

import android.accessibilityservice.AccessibilityService;
import android.util.Log;
import android.view.KeyEvent;
import android.view.accessibility.AccessibilityEvent;
import com.iiordanov.bVNC.RemoteCanvasActivity;
import com.iiordanov.bVNC.input.RemoteRdpKeyboard;
import java.util.Arrays;
import java.util.List;

public class KeyboardAccessibilityService extends AccessibilityService {

    private final static List<Integer> BAD = Arrays.asList(
        KeyEvent.KEYCODE_VOLUME_UP,
        KeyEvent.KEYCODE_VOLUME_DOWN,
        KeyEvent.KEYCODE_POWER
    );

    public boolean onKeyEvent(KeyEvent e) {
        if (!RemoteCanvasActivity.hasForegroundInstance) return super.onKeyEvent(e);
        if (BAD.contains(e.getKeyCode())) return super.onKeyEvent(e);
        if (RemoteRdpKeyboard.instance != null && RemoteRdpKeyboard.instance.keyboardActive) {
            if (e.getAction() == KeyEvent.ACTION_DOWN)
                RemoteRdpKeyboard.instance.sendKeyEvent(e, true);
            else
                RemoteRdpKeyboard.instance.sendKeyEvent(e, false);
            return true;
        }
        return super.onKeyEvent(e);
    }

    public void onServiceConnected() {
        super.onServiceConnected();
        Log.d("ACC", "connected");
    }

    public void onAccessibilityEvent(AccessibilityEvent e) {
    }

    public void onInterrupt() {
    }
}
