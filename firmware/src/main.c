#include "stm32f1xx_hal.h"

#include "board.h"
#include "control.h"
#include "protocol.h"
#include "robot_config.h"

UART_HandleTypeDef huart2;
TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim3;

static uint8_t rx_byte;

static void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_TIM1_Init(void);
static void MX_TIM3_Init(void);
static void MX_USART2_UART_Init(void);
static void Error_Handler(void);

int main(void)
{
    uint32_t last_control;
    uint32_t last_telemetry = 0u;
    uint32_t last_led = 0u;
    uint8_t led_on = 0u;

    HAL_Init();
    SystemClock_Config();

    MX_GPIO_Init();
    MX_TIM1_Init();
    MX_TIM3_Init();
    MX_USART2_UART_Init();

    control_init();
    protocol_init();

    HAL_UART_Receive_IT(&huart2, &rx_byte, 1u);

    last_control = HAL_GetTick();

    while (1) {
        uint32_t now;
        protocol_process();

        now = HAL_GetTick();

        if ((uint32_t)(now - last_control) >= ROBOT_CONTROL_PERIOD_MS) {
            float dt = (float)(now - last_control) / 1000.0f;
            uint8_t enabled;
            last_control = now;
            if (dt <= 0.0f) {
                dt = 0.001f;
            }
            enabled = protocol_is_alive(now);
            control_step(dt, enabled);
        }

        if ((uint32_t)(now - last_telemetry) >= ROBOT_TELEMETRY_PERIOD_MS) {
            last_telemetry = now;
            protocol_send_telemetry(now);
        }

        if ((uint32_t)(now - last_led) >= 500u) {
            last_led = now;
            led_on = led_on ? 0u : 1u;
            HAL_GPIO_WritePin(LED_PORT, LED_PIN, led_on ? GPIO_PIN_RESET : GPIO_PIN_SET);
        }
    }
}

static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clocks = {0};

    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_ON;
    osc.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLMUL = RCC_PLL_MUL9;
    if (HAL_RCC_OscConfig(&osc) != HAL_OK) {
        Error_Handler();
    }

    clocks.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                       RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clocks.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clocks.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clocks.APB1CLKDivider = RCC_HCLK_DIV2;
    clocks.APB2CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&clocks, FLASH_LATENCY_2) != HAL_OK) {
        Error_Handler();
    }
}

static void MX_TIM_PWM_Common(TIM_HandleTypeDef *htim)
{
    TIM_ClockConfigTypeDef clock_source = {0};
    TIM_MasterConfigTypeDef master = {0};
    TIM_OC_InitTypeDef channel = {0};

    htim->Init.Prescaler = 0u;
    htim->Init.CounterMode = TIM_COUNTERMODE_UP;
    htim->Init.Period = PWM_TIM_ARR;
    htim->Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim->Init.RepetitionCounter = 0u;
    htim->Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    if (HAL_TIM_PWM_Init(htim) != HAL_OK) {
        Error_Handler();
    }

    clock_source.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
    if (HAL_TIM_ConfigClockSource(htim, &clock_source) != HAL_OK) {
        Error_Handler();
    }

    master.MasterOutputTrigger = TIM_TRGO_RESET;
    master.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
    if (HAL_TIMEx_MasterConfigSynchronization(htim, &master) != HAL_OK) {
        Error_Handler();
    }

    channel.OCMode = TIM_OCMODE_PWM1;
    channel.Pulse = 0u;
    channel.OCPolarity = TIM_OCPOLARITY_HIGH;
    channel.OCNPolarity = TIM_OCNPOLARITY_HIGH;
    channel.OCFastMode = TIM_OCFAST_DISABLE;
    channel.OCIdleState = TIM_OCIDLESTATE_RESET;
    channel.OCNIdleState = TIM_OCNIDLESTATE_RESET;

    if (HAL_TIM_PWM_ConfigChannel(htim, &channel, TIM_CHANNEL_1) != HAL_OK) {
        Error_Handler();
    }
    if (HAL_TIM_PWM_ConfigChannel(htim, &channel, TIM_CHANNEL_2) != HAL_OK) {
        Error_Handler();
    }
    if (HAL_TIM_PWM_ConfigChannel(htim, &channel, TIM_CHANNEL_3) != HAL_OK) {
        Error_Handler();
    }
    if (HAL_TIM_PWM_ConfigChannel(htim, &channel, TIM_CHANNEL_4) != HAL_OK) {
        Error_Handler();
    }
}

static void MX_TIM1_Init(void)
{
    htim1.Instance = TIM1;
    MX_TIM_PWM_Common(&htim1);
}

static void MX_TIM3_Init(void)
{
    htim3.Instance = TIM3;
    MX_TIM_PWM_Common(&htim3);
}

static void MX_USART2_UART_Init(void)
{
    huart2.Instance = USART2;
    huart2.Init.BaudRate = UART_BAUDRATE;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    if (HAL_UART_Init(&huart2) != HAL_OK) {
        Error_Handler();
    }
}

static void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef init = {0};

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    HAL_GPIO_WritePin(LED_PORT, LED_PIN, GPIO_PIN_SET);
    init.Pin = LED_PIN;
    init.Mode = GPIO_MODE_OUTPUT_PP;
    init.Pull = GPIO_NOPULL;
    init.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(LED_PORT, &init);

    init.Mode = GPIO_MODE_IT_RISING_FALLING;
    init.Pull = GPIO_PULLUP;
    init.Speed = GPIO_SPEED_FREQ_HIGH;

    init.Pin = ENC1_A_PIN | ENC1_B_PIN;
    HAL_GPIO_Init(GPIOB, &init);

    init.Pin = ENC2_A_PIN | ENC2_B_PIN;
    HAL_GPIO_Init(GPIOB, &init);

    init.Pin = ENC3_A_PIN | ENC3_B_PIN;
    HAL_GPIO_Init(GPIOB, &init);

    init.Pin = ENC4_A_PIN | ENC4_B_PIN;
    HAL_GPIO_Init(GPIOB, &init);

    HAL_NVIC_SetPriority(EXTI9_5_IRQn, 1u, 0u);
    HAL_NVIC_EnableIRQ(EXTI9_5_IRQn);
    HAL_NVIC_SetPriority(EXTI15_10_IRQn, 1u, 0u);
    HAL_NVIC_EnableIRQ(EXTI15_10_IRQn);
}

void HAL_MspInit(void)
{
    __HAL_RCC_AFIO_CLK_ENABLE();
    __HAL_RCC_PWR_CLK_ENABLE();
}

void HAL_TIM_PWM_MspInit(TIM_HandleTypeDef *htim)
{
    GPIO_InitTypeDef init = {0};

    if (htim->Instance == TIM1) {
        __HAL_RCC_TIM1_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();
        init.Pin = GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10 | GPIO_PIN_11;
        init.Mode = GPIO_MODE_AF_PP;
        init.Speed = GPIO_SPEED_FREQ_HIGH;
        HAL_GPIO_Init(GPIOA, &init);
    } else if (htim->Instance == TIM3) {
        __HAL_RCC_TIM3_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();
        __HAL_RCC_GPIOB_CLK_ENABLE();

        init.Pin = GPIO_PIN_6 | GPIO_PIN_7;
        init.Mode = GPIO_MODE_AF_PP;
        init.Speed = GPIO_SPEED_FREQ_HIGH;
        HAL_GPIO_Init(GPIOA, &init);

        init.Pin = GPIO_PIN_0 | GPIO_PIN_1;
        HAL_GPIO_Init(GPIOB, &init);
    }
}

void HAL_UART_MspInit(UART_HandleTypeDef *huart)
{
    GPIO_InitTypeDef init = {0};

    if (huart->Instance == USART2) {
        __HAL_RCC_USART2_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();

        init.Pin = GPIO_PIN_2;
        init.Mode = GPIO_MODE_AF_PP;
        init.Speed = GPIO_SPEED_FREQ_HIGH;
        HAL_GPIO_Init(GPIOA, &init);

        init.Pin = GPIO_PIN_3;
        init.Mode = GPIO_MODE_INPUT;
        init.Pull = GPIO_PULLUP;
        HAL_GPIO_Init(GPIOA, &init);

        HAL_NVIC_SetPriority(USART2_IRQn, 2u, 0u);
        HAL_NVIC_EnableIRQ(USART2_IRQn);
    }
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2) {
        protocol_rx_byte(rx_byte);
        HAL_UART_Receive_IT(&huart2, &rx_byte, 1u);
    }
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2) {
        HAL_UART_Receive_IT(&huart2, &rx_byte, 1u);
    }
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2) {
        protocol_tx_complete();
    }
}

void SysTick_Handler(void)
{
    HAL_IncTick();
}

void USART2_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart2);
}

void EXTI9_5_IRQHandler(void)
{
    if (EXTI->PR & ENC1_A_PIN) {
        EXTI->PR = ENC1_A_PIN;
        control_encoder_isr(0u);
    }
    if (EXTI->PR & ENC1_B_PIN) {
        EXTI->PR = ENC1_B_PIN;
        control_encoder_isr(0u);
    }
    if (EXTI->PR & ENC2_A_PIN) {
        EXTI->PR = ENC2_A_PIN;
        control_encoder_isr(1u);
    }
    if (EXTI->PR & ENC2_B_PIN) {
        EXTI->PR = ENC2_B_PIN;
        control_encoder_isr(1u);
    }
}

void EXTI15_10_IRQHandler(void)
{
    if (EXTI->PR & ENC3_A_PIN) {
        EXTI->PR = ENC3_A_PIN;
        control_encoder_isr(2u);
    }
    if (EXTI->PR & ENC3_B_PIN) {
        EXTI->PR = ENC3_B_PIN;
        control_encoder_isr(2u);
    }
    if (EXTI->PR & ENC4_A_PIN) {
        EXTI->PR = ENC4_A_PIN;
        control_encoder_isr(3u);
    }
    if (EXTI->PR & ENC4_B_PIN) {
        EXTI->PR = ENC4_B_PIN;
        control_encoder_isr(3u);
    }
}

void HardFault_Handler(void)
{
    __disable_irq();
    while (1) {
    }
}

static void Error_Handler(void)
{
    __disable_irq();
    while (1) {
    }
}
