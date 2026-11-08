#ifndef MOTOR_H
#define MOTOR_H

#include <stdint.h>

/* ============================================================
 * MOTOR.H – API ĐIỀU KHIỂN MOTOR (RPWM/LPWM BTS7960)
 * - RPWM: TIM1 CH1–CH4 · LPWM: TIM3 CH1–CH4
 * ============================================================ */

void motor_init(void);
void motor_set(uint8_t index, float command);
void motor_stop_all(void);
void motor_brake_all(void);

#endif /* MOTOR_H */