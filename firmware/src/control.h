#ifndef CONTROL_H
#define CONTROL_H

#include <stdint.h>

/* ============================================================
 * CONTROL.H – API ĐIỀU KHIỂN ROBOT MECANUM
 * - Khởi tạo encoder, PID, motor
 * - Điều khiển vận tốc, RPM, manual, E-STOP
 * ============================================================ */

void control_init(void);
void control_set_velocity(float vx, float vy, float omega);
void control_set_wheel_rpm(const float rpm[4]);
void control_step(float dt, uint8_t enabled);
void control_stop(void);
void control_emergency_stop(void);
void control_set_manual(uint8_t index, float duty);
void control_encoder_isr(uint8_t index);
void control_get_actual_rpm(float out[4]);
void control_get_target_rpm(float out[4]);
void control_set_pid(uint8_t index, float kp, float ki, float kd);
void control_set_deadzone(uint8_t index, float deadzone);

#endif /* CONTROL_H */