#include "motor.h"

#include "stm32f1xx_hal.h"
#include "board.h"
#include "robot_config.h"

extern TIM_HandleTypeDef htim1;   /* RPWM bánh 1–4 */
extern TIM_HandleTypeDef htim3;   /* LPWM bánh 1–4 */

/* Cấu trúc channel cho mỗi motor BTS7960: (RPWM, LPWM) */
typedef struct {
    uint32_t rpwm_channel;
    uint32_t lpwm_channel;
} MotorChannel;

static const MotorChannel motors[4] = {
    { TIM_CHANNEL_1, TIM_CHANNEL_1 },
    { TIM_CHANNEL_2, TIM_CHANNEL_2 },
    { TIM_CHANNEL_3, TIM_CHANNEL_3 },
    { TIM_CHANNEL_4, TIM_CHANNEL_4 }
};

/* Khởi tạo 4 motor BTS7960:
 * - Bật RPWM (TIM1) và LPWM (TIM3)
 * - Đặt compare = 0 (dừng) */
void motor_init(void)
{
    uint8_t i;
    for (i = 0u; i < 4u; i++) {
        HAL_TIM_PWM_Start(&htim1, motors[i].rpwm_channel);
        HAL_TIM_PWM_Start(&htim3, motors[i].lpwm_channel);
        __HAL_TIM_SET_COMPARE(&htim1, motors[i].rpwm_channel, 0u);
        __HAL_TIM_SET_COMPARE(&htim3, motors[i].lpwm_channel, 0u);
    }
}

/* Đặt duty cho motor index (0..3) – BTS7960 (đã áp MOTOR_INVERT_MASK):
 * - command > 0: tiến → RPWM = duty, LPWM = 0
 * - command < 0: lùi  → RPWM = 0, LPWM = |duty|
 * - command = 0: dừng → cả hai = 0 (coast)
 * duty được clamp trong [-1,1] và map sang compare 0..PWM_TIM_ARR */
void motor_set(uint8_t index, float command)
{
    float magnitude;
    uint32_t compare;

    if (index >= 4u) return;

    /* Đảo chiều bánh bị đấu dây ngược (xem board.h). Encoder của cùng bánh
     * phải được đảo tương ứng qua ENCODER_INVERT_MASK để PID giữ đúng dấu. */
    if (((MOTOR_INVERT_MASK) >> index) & 1u) {
        command = -command;
    }

    if (command > 1.0f) command = 1.0f;
    else if (command < -1.0f) command = -1.0f;

    magnitude = (command < 0.0f) ? -command : command;
    compare = (uint32_t)(magnitude * (float)PWM_TIM_ARR + 0.5f);
    if (compare > PWM_TIM_ARR) compare = PWM_TIM_ARR;

    if (command >= 0.0f) {
        __HAL_TIM_SET_COMPARE(&htim1, motors[index].rpwm_channel, compare);
        __HAL_TIM_SET_COMPARE(&htim3, motors[index].lpwm_channel, 0u);
    } else {
        __HAL_TIM_SET_COMPARE(&htim1, motors[index].rpwm_channel, 0u);
        __HAL_TIM_SET_COMPARE(&htim3, motors[index].lpwm_channel, compare);
    }
}

/* Dừng tất cả motor: RPWM = 0, LPWM = 0 (coast)
 * An toàn khi gọi rất sớm/HardFault: nếu TIM chưa init thì bỏ qua. */
void motor_stop_all(void)
{
    uint8_t i;
    if (htim1.Instance == NULL || htim3.Instance == NULL) {
        return;
    }
    for (i = 0u; i < 4u; i++) {
        __HAL_TIM_SET_COMPARE(&htim1, motors[i].rpwm_channel, 0u);
        __HAL_TIM_SET_COMPARE(&htim3, motors[i].lpwm_channel, 0u);
    }
}

/* Phanh tất cả motor: RPWM = LPWM = 100%
 * (BTS7960 active braking: cả hai đầu vào mức cao) */
void motor_brake_all(void)
{
    uint8_t i;
    for (i = 0u; i < 4u; i++) {
        __HAL_TIM_SET_COMPARE(&htim1, motors[i].rpwm_channel, PWM_TIM_ARR);
        __HAL_TIM_SET_COMPARE(&htim3, motors[i].lpwm_channel, PWM_TIM_ARR);
    }
}
