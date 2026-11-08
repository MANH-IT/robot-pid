#include "pid.h"

#include <math.h>

#include "robot_config.h"

/* Giới hạn giá trị trong khoảng [low, high] */
static float clampf(float value, float low, float high)
{
    if (value < low) {
        return low;
    }
    if (value > high) {
        return high;
    }
    return value;
}

/* Khởi tạo PID:
 * - kp, ki, kd: hệ số P/I/D
 * - deadzone: bù dead-zone cho encoder
 * - Đặt i_term, prev_meas, d_filtered về 0 */
void pid_init(PidController *pid, float kp, float ki, float kd, float deadzone)
{
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->i_term = 0.0f;
    pid->prev_meas = 0.0f;
    pid->d_filtered = 0.0f;
    pid->out_min = PID_OUT_MIN;
    pid->out_max = PID_OUT_MAX;
    pid->i_min = PID_I_MIN;
    pid->i_max = PID_I_MAX;
    pid->deadzone = deadzone;
    pid->has_prev = 0u;
}

/* Cập nhật gains PID (không reset integral) */
void pid_set_gains(PidController *pid, float kp, float ki, float kd)
{
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
}

/* Cài đặt dead-zone (clamp trong [0, 0.5]) */
void pid_set_deadzone(PidController *pid, float deadzone)
{
    pid->deadzone = clampf(deadzone, 0.0f, 0.5f);
}

/* Reset PID:
 * - i_term = 0
 * - prev_meas = measurement hiện tại
 * - d_filtered = 0, has_prev = 1 */
void pid_reset(PidController *pid, float measurement)
{
    pid->i_term = 0.0f;
    pid->prev_meas = measurement;
    pid->d_filtered = 0.0f;
    pid->has_prev = 1u;
}

/* Cập nhật PID:
 * - error = setpoint - measurement
 * - P = Kp * error
 * - D = -Kd * d(measurement)/dt (derivative-on-measurement)
 * - I có anti-windup: chỉ tích phân khi chưa bão hòa
 * - Bù dead-zone nếu cùng dấu với setpoint
 * - Output clamp [-1,1] */
float pid_update(PidController *pid, float setpoint, float measurement, float dt)
{
    float error;
    float p_term;
    float d_term;
    float d_raw;
    float i_candidate;
    float out_candidate;

    if (dt <= 0.0f) {
        return 0.0f;
    }

    if (!pid->has_prev) {
        pid_reset(pid, measurement);
    }

    error = setpoint - measurement;
    p_term = pid->kp * error;

    d_raw = (measurement - pid->prev_meas) / dt;
    pid->d_filtered += PID_D_FILTER_ALPHA * (d_raw - pid->d_filtered);
    d_term = -pid->kd * pid->d_filtered;
    pid->prev_meas = measurement;

    i_candidate = clampf(pid->i_term + pid->ki * error * dt, pid->i_min, pid->i_max);
    out_candidate = p_term + i_candidate + d_term;

    if (!((out_candidate >= pid->out_max && error > 0.0f) ||
          (out_candidate <= pid->out_min && error < 0.0f))) {
        pid->i_term = i_candidate;
    }

    out_candidate = p_term + pid->i_term + d_term;

    if (setpoint > 0.0f && out_candidate > 0.0f) {
        out_candidate += pid->deadzone;
    } else if (setpoint < 0.0f && out_candidate < 0.0f) {
        out_candidate -= pid->deadzone;
    }

    return clampf(out_candidate, pid->out_min, pid->out_max);
}
