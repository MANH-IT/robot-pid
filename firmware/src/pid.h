#ifndef PID_H
#define PID_H

#include <stdint.h>

typedef struct {
    float kp;
    float ki;
    float kd;
    float i_term;
    float prev_meas;
    float d_filtered;
    float out_min;
    float out_max;
    float i_min;
    float i_max;
    float deadzone;
    uint8_t has_prev;
} PidController;

void pid_init(PidController *pid, float kp, float ki, float kd, float deadzone);
void pid_set_gains(PidController *pid, float kp, float ki, float kd);
void pid_set_deadzone(PidController *pid, float deadzone);
void pid_reset(PidController *pid, float measurement);
float pid_update(PidController *pid, float setpoint, float measurement, float dt);

#endif
