#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2013 Bitcraze AB
#
#  Crazyflie Nano Quadcopter Client
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.

import math
import zmq
from collections import namedtuple
import time

Reference = namedtuple("Reference", 'x y z yaw', verbose=False, rename=False)
Configurator = namedtuple("gains", 'p i d set', verbose=False, rename=False)
PidOutputs = namedtuple("PidOutputs", 'roll pitch yaw thrust')


class PID_V(object):
    """
    Discrete PID control
    """

    def __init__(self, p=0, i=0, d=0, set_point=0, set_point_max=1, set_point_min=-1, saturate_max=None, saturate_min=None):

        self.kp = p
        self.Ki = i
        self.Kd = d
        self._Ti = self.kp / self.Ki
        self._Td = self.kd / self.kp
        self.prev_time = 0
        self.dt = 0

        self.set_point_max = set_point_max
        self.set_point_min = set_point_min
        self.set_point = set_point
        self.saturate_max = saturate_max
        self.saturate_min = saturate_min

        self.ut = 0.0    # the output
        self.ut_1 = 0.0  # the last output
        self.et = 0.0    # the error
        self.et_1 = 0.0  # the last error
        self.et_2 = 0.0  # ...

    def update(self, feedback):
        """
        Calculate PID output value for given reference input and feedback
        :param feedback: state of the plant
        """
        self.dt = (time.time() - self.prev_t)
        self.prev_time = time.time()
        self.et = self.set_point - feedback
        self.ut = self.ut_1 + self.kp * (
            (1 + self.dt / self._Ti + self._Td / self.dt) * self.et - (1 + 2 * self._Td / self.dt) * self.et_1
            + (self._Td * self.et_2) / self.dt)

        self.et_2 = self.et_1
        self.et_1 = self.et
        self.ut_1 = self.ut

        return self.ut

    @property
    def kp(self):
        return self._kp

    @kp.setter
    def kp(self, p):
        """

        :param P:
        """
        self._Kp = p
        self._Ti = self._kp / self.ki
        self._Td = self.kd / self._kp

    @property
    def ki(self):
        return self._Ki


    @Ki.setter
    def ki(self, i):
        self._Ki = i
        self._Ti = self.kp / self._ki
        self._Td = self.kd / self.kp

    @property
    def kd(self):
        return self._kd


    @kd.setter
    def kd(self, d):
        self._kd = d
        self._Ti = self.kp / self.ki
        self._Td = self._kd / self.kp

    @property
    def set_point(self):
        return self._set_point

    @set_point.setter
    def set_point(self, set_point):
        if set_point > self.set_point_max:
            self._set_point = self.set_point_max
        elif set_point < self.set_point_min:
            self._set_point = self.set_point_min
        else:
            self._set_point = set_point

        # @todo: ask the professor about this
        self.ut = 0
        self.ut_1 = 0

    @property
    def ut(self):
        return self._ut

    @ut.setter
    def ut(self, ut):
        self._ut = ut

        if self.saturate_max or self.saturate_min:
            if self.saturate_max and ut > self.saturate_max:
                self._ut = self.saturate_max
            elif self.saturate_min and ut < self.saturate_min:
                self._ut = self.saturate_min

class PID:

    def __init__(self, name="N/A", P=1.0, I=0.0, D=10.0, Derivator=0, Integrator=0,
                 Integrator_max=300, Integrator_min=-200, set_point=0.0,
                 power=1.0, zmq_connection=None):
        self._zmq = zmq_connection
        self.Kp=P
        self.Ki=I
        self.Kd=D
        self.Derivator=Derivator
        self.power = power
        self.Integrator=Integrator
        self.Integrator_max=Integrator_max
        self.Integrator_min=Integrator_min
        self.last_error = 0.0
        self.last_value = 0.0

        self.set_point=set_point
        self.error=0.0


        self._z_data = {
            "name": name,
            "data": {
                "P": 0.1,
                "I": 0.1,
                "D": 0.0,
                "E": 0.0,
                "SP": 0.0,
            }
        }


    def update(self,current_value):
        """
        Calculate PID output value for given reference input and feedback
        """

        self.error = self.set_point - current_value

        self.P_value = self.Kp * self.error
        if (self.last_value >= current_value):
            change = self.error - self.last_error
        else:
            change = 0.0

        if self.error > 0.0:
            self.I_value = self.Integrator * self.Ki
        else:
            self.I_value = (self.Integrator * self.Ki)


        #self.D_value = self.Kd * ( self.error - self.Derivator)
        self.D_value = self.Kd * change
        self.Derivator = self.error

        self.Integrator = self.Integrator + self.error

        if self.Integrator > self.Integrator_max:
            self.Integrator = self.Integrator_max
        elif self.Integrator < self.Integrator_min:
            self.Integrator = self.Integrator_min

        self.last_error = self.error
        self.last_value = current_value

        PID = self.P_value + self.I_value + self.D_value

        self._z_data["data"]["P"] = self.P_value
        self._z_data["data"]["I"] = self.I_value
        self._z_data["data"]["D"] = self.D_value
        self._z_data["data"]["E"] = self.error
        self._z_data["data"]["SP"] = self.set_point
        self._z_data["data"]["OUT"] = PID

        if self._zmq:
            try:
                self._zmq.send_json(self._z_data, zmq.NOBLOCK)
            except zmq.error.Again:
                pass

        return PID

    def set_point(self,set_point):
        """Initilize the setpoint of PID"""
        self.set_point = set_point
        self.Integrator=0
        self.Derivator=0

class PID_RP:

    def __init__(self, name="N/A", P=1.0, I=0.0, D=10.0, Derivator=0, Integrator=0,
                 Integrator_max=20000, Integrator_min=-20000, set_point=0.0,
                 power=1.0, zmq_connection=None):

        self._zmq = zmq_connection
        self.Kp=P
        self.Ki=I
        self.Kd=D
        self.name = name
        self.Derivator=Derivator
        self.power = power
        self.Integrator=Integrator
        self.Integrator_max=Integrator_max
        self.Integrator_min=Integrator_min
        self.last_error = 0.0
        self.last_value = 0.0

        self.set_point=set_point
        self.error=0.0

        self.prev_t = 0

        self._z_data = {
            "name": name,
            "data": {
                "P": 0.0,
                "I": 0.0,
                "D": 0.0,
                "E": 0.0,
                "SP": 0.0,
                "OUT": 0.0
            }
        }

    def reset_dt(self):
        self.prev_t = time.time()

    def update(self, current_value):
        """
        Calculate PID output value for given reference input and feedback
        """

        dt = (time.time() - self.prev_t)
        self.prev_t = time.time()
        self.error = self.set_point - current_value

        self.P_value = self.Kp * self.error
        change = self.error - self.last_error

        self.I_value = self.Integrator * self.Ki * dt

        #self.D_value = self.Kd * ( self.error - self.Derivator)
        self.D_value = self.Kd * change / dt
        self.Derivator = self.error

        self.Integrator = self.Integrator + self.error

        if self.Integrator > self.Integrator_max:
            self.Integrator = self.Integrator_max
        elif self.Integrator < self.Integrator_min:
            self.Integrator = self.Integrator_min

        self.last_error = self.error
        self.last_value = current_value

        #print "{}: P={}, I={}, D={}".format(self.name, self.P_value, self.I_value, self.D_value)

        PID = self.P_value + self.I_value + self.D_value

        self._z_data["data"]["P"] = self.P_value
        self._z_data["data"]["I"] = self.I_value
        self._z_data["data"]["D"] = self.D_value
        self._z_data["data"]["E"] = self.error
        self._z_data["data"]["SP"] = self.set_point
        self._z_data["data"]["OUT"] = PID

        if self._zmq:
            try:
                self._zmq.send_json(self._z_data, zmq.NOBLOCK)
            except zmq.error.Again:
                pass

        return PID

    def set_point(self,set_point):
        """
        Initilize the setpoint of PID
        """
        self.set_point = set_point
        self.Integrator=0
        self.Derivator=0

