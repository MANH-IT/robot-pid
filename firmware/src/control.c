#include "control.h"

#include "board.h"
#include "encoder.h"
#include "motor.h"
#include "pid.h"
#include "robot_config.h"

extern TIM_HandleTypeDef htim2;
extern TIM_HandleTypeDef htim3;
extern TIM_HandleTypeDef htim4;

static Encoder encoders[4];
static PidController pids[4];
static float target_rpm[4];
static float actual_rpm[4];
static uint8_t manual_active;
static uint8_t manual_index;
static float manual_duty;
static volatile uint8_t emergency_flag;

static float clampf(float value, float low, float high)
{
    if (value < low) return low;
    if (value > high) return high;
    return value;
}

void control_init(void) // Khởi tạo encoder, PID, đặt emergency_flag = 0
{
    uint8_t index;

    encoder_init(&encoders[0], ENCODER_1, &htim2,
                 ENC1_A_PORT, ENC1_A_PIN,
                 ENC1_B_PORT, ENC1_B_PIN, ENC1_INVERT);

    encoder_init(&encoders[1], ENCODER_2, &htim3,
                 ENC2_A_PORT, ENC2_A_PIN,
                 ENC2_B_PORT, ENC2_B_PIN, ENC2_INVERT);

    encoder_init(&encoders[2], ENCODER_3, &htim4,
                 ENC3_A_PORT, ENC3_A_PIN,
                 ENC3_B_PORT, ENC3_B_PIN, ENC3_INVERT);

    encoder_init(&encoders[3], ENCODER_4, NULL,
                 ENC4_A_PORT, ENC4_A_PIN,
                 ENC4_B_PORT, ENC4_B_PIN, ENC4_INVERT);

    for (index = 0u; index < 4u; index++) {
        pid_init(&pids[index], PID_KP_DEFAULT, PID_KI_DEFAULT, PID_KD_DEFAULT, DEADZONE_DEFAULT);
        target_rpm[index] = 0.0f;
        actual_rpm[index] = 0.0f;
    }

    manual_active = 0u;
    manual_index = 0u;
    manual_duty = 0.0f;
    emergency_flag = 0u;

    motor_init();
}

void control_set_velocity(float vx, float vy, float omega)
// Tính kinematic inverse: chuyển vận tốc thân (vx, vy, omega) thành RPM 4 bánh
{
    float radius = WHEEL_RADIUS_M;
    float arm = YAW_ARM_M;
    float rpm_scale = 60.0f / (2.0f * 3.14159265358979f);
    float w1, w2, w3, w4;
    float peak, scale;
    float rpm[4];

    if (manual_active) {
        manual_active = 0u;
        for (uint8_t i = 0u; i < 4u; i++) {
            pid_reset(&pids[i], actual_rpm[i]);
        }
    }

#if VY_INVERTED
    vy = -vy;
#endif
#if OMEGA_INVERTED
    omega = -omega;
#endif

    w1 = (vx - vy - arm * omega) / radius;
    w2 = (vx + vy + arm * omega) / radius;
    w3 = (vx + vy - arm * omega) / radius;
    w4 = (vx - vy + arm * omega) / radius;

    rpm[0] = w1 * rpm_scale;
    rpm[1] = w2 * rpm_scale;
    rpm[2] = w3 * rpm_scale;
    rpm[3] = w4 * rpm_scale;

    peak = 0.0f;
    for (uint8_t i = 0u; i < 4u; i++) {
        float mag = rpm[i] < 0.0f ? -rpm[i] : rpm[i];
        if (mag > peak) peak = mag;
    }
    if (peak > MAX_WHEEL_RPM && peak > 0.0f) {
        scale = MAX_WHEEL_RPM / peak;
        for (uint8_t i = 0u; i < 4u; i++) {
            rpm[i] *= scale;
        }
    }

    control_set_wheel_rpm(rpm);
}

void control_set_wheel_rpm(const float rpm[4])
{
    uint8_t index;

    if (manual_active) {
        manual_active = 0u;
        for (index = 0u; index < 4u; index++) {
            pid_reset(&pids[index], actual_rpm[index]);
        }
    }
    for (index = 0u; index < 4u; index++) {
        target_rpm[index] = clampf(rpm[index], -MAX_WHEEL_RPM, MAX_WHEEL_RPM);
    }
}

void control_step(float dt, uint8_t enabled)
// Vòng lặp điều khiển 10 ms: đọc encoder, tính RPM, cập PID, điều khiển motor
{
    uint8_t index;
    float pid_dt;

    if (dt <= 0.0f) return;

    for (index = 0u; index < 4u; index++) {
        int32_t delta = encoder_take_delta(&encoders[index]);
        actual_rpm[index] = (float)delta * 60.0f / (ENCODER_CPR * dt);
    }

    pid_dt = dt > 0.05f ? 0.05f : dt;

    if (!enabled || emergency_flag) {
        manual_active = 0u;
        for (index = 0u; index < 4u; index++) {
            target_rpm[index] = 0.0f;
            pid_reset(&pids[index], actual_rpm[index]);
        }
        motor_stop_all();
        return;
    }

    if (manual_active) {
        for (index = 0u; index < 4u; index++) {
            if (index != manual_index) {
                motor_set(index, 0.0f);
            }
        }
        motor_set(manual_index, manual_duty);
        return;
    }

    for (index = 0u; index < 4u; index++) {
        float output = pid_update(&pids[index], target_rpm[index], actual_rpm[index], pid_dt);
        motor_set(index, output);
    }
}

void control_stop(void)
// Dừng tất cả motor, reset target_rpm và PID
{
    uint8_t index;
    manual_active = 0u;
    for (index = 0u; index < 4u; index++) {
        target_rpm[index] = 0.0f;
        pid_reset(&pids[index], actual_rpm[index]);
    }
    motor_stop_all();
}

void control_emergency_stop(void)
// Khẩn cấp: dừng PWM, đặt cờ emergency_flag, reset PID,setpoint
{
    uint8_t index;
    emergency_flag = 1u;
    manual_active = 0u;
    motor_stop_all();
    for (index = 0u; index < 4u; index++) {
        target_rpm[index] = 0.0f;
        pid_reset(&pids[index], actual_rpm[index]);
    }
}

void control_set_manual(uint8_t index, float duty)
// Đặt manual mode cho bánh index, duty [-1,1] điều khiển trực tiếp PWM
{
    if (index >= 4u) return;

    if (!manual_active || manual_index != index) {
        manual_index = index;
        for (uint8_t i = 0u; i < 4u; i++) {
            target_rpm[i] = 0.0f;
            pid_reset(&pids[i], actual_rpm[i]);
        }
        motor_stop_all();
    }
    manual_active = 1u;
    manual_duty = clampf(duty, -1.0f, 1.0f);
}

void control_encoder_isr(uint8_t index)
{
    if (index < 4u) {
        encoder_handle_edge(&encoders[index]);
    }
}

void control_get_actual_rpm(float out[4])
// Đọc RPM thực tế của 4 bánh từ encoder
{
    uint8_t index;
    for (index = 0u; index < 4u; index++) {
        out[index] = actual_rpm[index];
    }
}

void control_get_target_rpm(float out[4])
// Đọc target RPM được gửi từ host hoặc tính từ lệnh V
{
    uint8_t index;
    for (index = 0u; index < 4u; index++) {
        out[index] = target_rpm[index];
    }
}

void control_set_pid(uint8_t index, float kp, float ki, float kd)
// Cập nhật gains PID cho bánh index, reset PID integral
{
    if (index < 4u) {
        pid_set_gains(&pids[index], kp, ki, kd);
        pid_reset(&pids[index], actual_rpm[index]);
    }
}

void control_set_deadzone(uint8_t index, float deadzone)
// Cài đặt dead-zone cho bánh index (0..0.5)
{
    if (index < 4u) {
        pid_set_deadzone(&pids[index], deadzone);
    }
}