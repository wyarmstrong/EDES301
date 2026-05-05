"""
--------------------------------------------------------------------------
Button Driver
--------------------------------------------------------------------------
License:   
Copyright 2021-2024 - Wyatt Armstrong

Redistribution and use in source and binary forms, with or without 
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this 
list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, 
this list of conditions and the following disclaimer in the documentation 
and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors 
may be used to endorse or promote products derived from this software without 
specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
--------------------------------------------------------------------------
"""
import time
import Adafruit_BBIO.GPIO as GPIO

# ------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------

HIGH = GPIO.HIGH
LOW  = GPIO.LOW

# ------------------------------------------------------------------------
# Button Class
# ------------------------------------------------------------------------

class Button():
    """ Button Driver for BeagleBone connected to P2_02 (GPIO 59) """

    pin                       = None
    unpressed_value           = None
    pressed_value             = None
    sleep_time                = None
    press_duration            = None

    pressed_callback          = None
    pressed_callback_value    = None
    unpressed_callback        = None
    unpressed_callback_value  = None
    on_press_callback         = None
    on_press_callback_value   = None
    on_release_callback       = None
    on_release_callback_value = None


    def __init__(self, pin=None, sleep_time=0.1, active_low=True):
        """
        Initialize variables and set up the button.

        Parameters:
          pin        : BeagleBone pin name (e.g. "P2_2")
          sleep_time : Polling interval in seconds (default 0.1 s)
          active_low : True  → pull-up config (pin HIGH when not pressed)
                       False → pull-down config (pin LOW when not pressed)
        """
        if pin is None:
            raise ValueError("Pin not provided for Button()")
        self.pin = pin

        # Set logic levels based on resistor configuration
        if active_low:
            self.unpressed_value = HIGH   # Pin reads HIGH when open (pull-up)
            self.pressed_value   = LOW    # Pin reads LOW  when pressed to GND
        else:
            self.unpressed_value = LOW    # Pin reads LOW  when open (pull-down)
            self.pressed_value   = HIGH   # Pin reads HIGH when pressed to VCC

        self.sleep_time     = sleep_time
        self.press_duration = 0.0

        self._setup()

    # End def


    # ------------------------------------------------------------------
    # HW#4 TODO (a): _setup()
    # ------------------------------------------------------------------
    def _setup(self):
        """
        Configure the GPIO pin as an input.

        The BeagleBone pin P2_02 maps to GPIO 59.
        GPIO.setup() puts the pin in input mode so we can read button state.
        """
        GPIO.setup(self.pin, GPIO.IN)   # <-- HW#4 implementation

    # End def


    # ------------------------------------------------------------------
    # HW#4 TODO (b): is_pressed()
    # ------------------------------------------------------------------
    def is_pressed(self):
        """
        Return True if the button is currently pressed, False otherwise.

        GPIO.input() reads the current logic level on the pin.
        We compare it to pressed_value (LOW for active-low, HIGH for active-high).
        This call consumes no waiting time — it is an instantaneous snapshot.
        """
        return GPIO.input(self.pin) == self.pressed_value   # <-- HW#4 implementation

    # End def


    # ------------------------------------------------------------------
    # HW#4 TODO (c): wait_for_press()
    # ------------------------------------------------------------------
    def wait_for_press(self):
        """
        Block until the button is fully pressed AND released.

        Sequence:
          1. Poll until pin leaves unpressed_value  → button pressed
          2. Record press start time & fire on_press_callback (once)
          3. Poll until pin leaves pressed_value    → button released
          4. Calculate and store press duration
          5. Fire on_release_callback (once)

        While polling, the appropriate callback is called every sleep_time
        seconds so the application can do work (e.g. update an LED).
        """
        button_press_time = None

        # --- Wait for button PRESS ---
        while GPIO.input(self.pin) == self.unpressed_value:    # <-- HW#4 implementation
            if self.unpressed_callback is not None:
                self.unpressed_callback_value = self.unpressed_callback()
            time.sleep(self.sleep_time)

        # Record the moment the press was detected
        button_press_time = time.time()                        # <-- HW#4 implementation

        # Fire on_press callback exactly once
        if self.on_press_callback is not None:
            self.on_press_callback_value = self.on_press_callback()

        # --- Wait for button RELEASE ---
        while GPIO.input(self.pin) == self.pressed_value:      # <-- HW#4 implementation
            if self.pressed_callback is not None:
                self.pressed_callback_value = self.pressed_callback()
            time.sleep(self.sleep_time)

        # Calculate total press duration
        self.press_duration = time.time() - button_press_time  # <-- HW#4 implementation

        # Fire on_release callback exactly once
        if self.on_release_callback is not None:
            self.on_release_callback_value = self.on_release_callback()

    # End def


    def get_last_press_duration(self):
        """ Return the duration (seconds) of the last button press. """
        return self.press_duration

    # End def


    def cleanup(self):
        """ Clean up the button hardware (nothing needed for GPIO input). """
        pass

    # End def


    # ------------------------------------------------------------------
    # Callback setters / getters
    # ------------------------------------------------------------------

    def set_pressed_callback(self, function):
        """ Called every sleep_time while button IS pressed. """
        self.pressed_callback = function

    def get_pressed_callback_value(self):
        return self.pressed_callback_value

    def set_unpressed_callback(self, function):
        """ Called every sleep_time while button is NOT pressed. """
        self.unpressed_callback = function

    def get_unpressed_callback_value(self):
        return self.unpressed_callback_value

    def set_on_press_callback(self, function):
        """ Called once the moment the button is pressed. """
        self.on_press_callback = function

    def get_on_press_callback_value(self):
        return self.on_press_callback_value

    def set_on_release_callback(self, function):
        """ Called once the moment the button is released. """
        self.on_release_callback = function

    def get_on_release_callback_value(self):
        return self.on_release_callback_value

# End class


# ------------------------------------------------------------------------
# Main script — run with: python3 button.py
# ------------------------------------------------------------------------

if __name__ == '__main__':

    print("Button Test")

    button = Button("P2_2")   # P2_02 = GPIO 59, active-low (pull-up default)

    # Define callback functions
    def pressed():
        print("  [callback] Button is being held down...")

    def unpressed():
        print("  [callback] Waiting for press...")

    def on_press():
        print("  [callback] Button was just pressed!")
        return 3

    def on_release():
        print("  [callback] Button was just released!")
        return 4

    try:
        # --- Test 1: is_pressed() snapshot ---
        print("\n[Test 1] Is the button pressed right now?")
        print("  Result: {0}".format(button.is_pressed()))

        print("  >>> Hold the button down, then wait 4 seconds...")
        time.sleep(4)
        print("  Is the button pressed now? {0}".format(button.is_pressed()))

        print("  >>> Release the button, then wait 4 seconds...")
        time.sleep(4)

        # --- Test 2: wait_for_press() without callbacks ---
        print("\n[Test 2] Waiting for a button press (no callbacks)...")
        button.wait_for_press()
        print("  Button held for {0:.3f} seconds.".format(button.get_last_press_duration()))

        # --- Test 3: wait_for_press() with callbacks ---
        print("\n[Test 3] Setting callback functions...")
        button.set_pressed_callback(pressed)
        button.set_unpressed_callback(unpressed)
        button.set_on_press_callback(on_press)
        button.set_on_release_callback(on_release)

        print("Waiting for button press with callbacks active...")
        button.wait_for_press()
        print("  Button held for {0:.3f} seconds.".format(button.get_last_press_duration()))
        print("  pressed  callback value    = {0}".format(button.get_pressed_callback_value()))
        print("  unpressed callback value   = {0}".format(button.get_unpressed_callback_value()))
        print("  on_press callback value    = {0}".format(button.get_on_press_callback_value()))
        print("  on_release callback value  = {0}".format(button.get_on_release_callback_value()))

    except KeyboardInterrupt:
        print("\nTest interrupted by user (Ctrl-C).")

    finally:
        button.cleanup()

    print("\nTest Complete")