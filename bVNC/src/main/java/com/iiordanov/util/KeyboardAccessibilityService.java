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

    private static final String TAG = "aRDPAccessibility";
    private final static List<Integer> BLACKLISTED_KEYS = Arrays.asList(KeyEvent.KEYCODE_VOLUME_UP, KeyEvent.KEYCODE_VOLUME_DOWN, KeyEvent.KEYCODE_POWER);

    @Override
    public boolean onKeyEvent(KeyEvent event) {

        if (!RemoteCanvasActivity.hasForegroundInstance) {
            // If the app is not in the foreground, we don't want to process the key event
            return super.onKeyEvent(event);
        }

        int action = event.getAction();
        int keyCode = event.getKeyCode();
        boolean isMod = KeyEvent.isModifierKey(keyCode);

        Log.d(TAG, "onKeyEvent: code " + keyCode + ", action " + action + ", modifier " + isMod);

        if (RemoteRdpKeyboard.instance != null && RemoteRdpKeyboard.instance.isConnected() && !BLACKLISTED_KEYS.contains(keyCode)) {
            if (action == KeyEvent.ACTION_DOWN) {
                if (!isMod) {
                    RemoteRdpKeyboard.instance.repeatKeyEvent(keyCode, event);
                } else {
                    RemoteRdpKeyboard.instance.processLocalKeyEvent(keyCode, event, 0);
                }
                return true;
            } else if (action == KeyEvent.ACTION_UP) {
                if (!isMod) {
                    RemoteRdpKeyboard.instance.stopRepeatingKeyEvent();
                } else {
                    RemoteRdpKeyboard.instance.processLocalKeyEvent(keyCode, event, 0);
                }
                return true;
            }
        }

        Log.d(TAG, "onKeyEvent: no active connection, key event not processed");
        return super.onKeyEvent(event);
    }

    @Override
    public void onServiceConnected() {
        Log.i(TAG, "onServiceConnected: Keyboard service is connected");
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent accessibilityEvent) {

    }

    @Override
    public void onInterrupt() {

    }
}
