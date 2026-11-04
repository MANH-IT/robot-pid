#ifndef MOTOR_H
#define MOTOR_H

#include <stdint.h>

void motor_init(void);
void motor_set(uint8_t index, float command);
void motor_stop_all(void);

#endif
