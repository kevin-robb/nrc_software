#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>
#include <RobotLib.h>


#define DEVICE_ID 1


/////////////////////////////////
// Actuators
/////////////////////////////////

// Drivetrain motors
Motor leftMotor, rightMotor;

// Drivetrain output parameters
float turnPower;
float drivePower = 0.25;



/////////////////////////////////
// Algorithms
/////////////////////////////////

// Heading control
PIDController yawController;
float targetAngle = 0.0;

// Velocity Estimators
TrackingLoop left_tracking, right_tracking;



/////////////////////////////////
// Communications
/////////////////////////////////

// Serial Send/Receive
StaticJsonDocument<256> recv_pkt;
StaticJsonDocument<256> send_pkt;



/////////////////////////////////
// Sensors
/////////////////////////////////
#define LEFT_ENC_A 0
#define LEFT_ENC_B 0
#define RIGHT_ENC_A 0
#define RIGHT_ENC_B 0

// BNO055
Adafruit_BNO055 bno = Adafruit_BNO055(55);
imu::Vector<3> euler;
sensors_event_t event;

// Encoders
QuadratureEncoder leftEncoder, rightEncoder;



/////////////////////////////////
// Angle Helper Functions
/////////////////////////////////

float constrainAngle(float x)
{
    x = fmod(x + 180,360);
    if (x < 0)
        x += 360;
    return x - 180;
}

float angleDiff(float a,float b)
{
    float dif = fmod(b - a + 180,360);
    if (dif < 0)
        dif += 360;
    return dif - 180;
}



/////////////////////////////////
// Interrupt Handlers
/////////////////////////////////

// Left Encoder
void left_encoder_isr()
{
    left_encoder.process();
}

// Right Encoder
void right_encoder_isr()
{
    right_encoder.process();
}



/////////////////////////////////
// Arduino Functions
/////////////////////////////////

void setup()
{
    Serial.begin(9600);

    /* Initialise the sensor */
    if(!bno.begin())
    {
        /* There was a problem detecting the BNO055 ... check your connections */
        Serial.print("Ooops, no BNO055 detected ... Check your wiring or I2C ADDR!");
        while(1);
    }

    delay(1000);

    // Enable the external crystal on the IMU
    bno.setExtCrystalUse(true);

    // Set up the yaw PID controller
    yawController.begin(0, 0.01, 0, 0);

    // Set up the motors
    leftMotor.begin(4,5,6);
    rightMotor.begin(8,7,9);

    // Set up the encoders
    leftEncoder.begin(LEFT_ENC_A, LEFT_ENC_B);
    rightEncoder.begin(RIGHT_ENC_A, RIGHT_ENC_B);

    // Attach encoder interrupts
    attachInterrupt(digitalPinToInterrupt(LEFT_ENC_A), &left_encoder_isr, CHANGE);
    attachInterrupt(digitalPinToInterrupt(RIGHT_ENC_A), &right_encoder_isr, CHANGE);
}



void loop()
{
    // BNO055 sensor data
    bno.getEvent(&event);
    euler = bno.getVector(Adafruit_BNO055::VECTOR_EULER);


    // Tracking loops for wheel velocities
    left_tracking.update(left_encoder.getValue());
    right_tracking.update(right_encoder.getValue());


    // Sensor data update
    send_pkt["id"] = DEVICE_ID;
    send_pkt["yaw"] = euler.x();
    send_pkt["left_vel"] = left_tracking.getVelocityEstimate();
    send_pkt["right_vel"] = right_tracking.getVelocityEstimate();

    // Send data over serial
    serializeJson(send_pkt, Serial);


    ////////////////////////////////////////////////////////////////////////////////////////////


    // Get commands from serial
    if(Serial.available())
    {
        deserializeJson(recv_pkt, Serial);

        //drivePower = recv_pkt["drive_power"];   // TODO: replace with target velocity and then make a PID for drive power
        targetAngle = recv_pkt["target_yaw"];
    }

    // Achieve the current target heading by locking the IMU to the desired yaw
    turnPower = yawController.update(0, angleDiff(constrainAngle(euler.x()), targetAngle));

    // Output to the motors
    leftMotor.output(drivePower - turnPower);
    rightMotor.output(drivePower + turnPower);

}