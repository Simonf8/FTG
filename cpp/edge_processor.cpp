/**
 * High-Performance Edge Processor (C++)
 * Low-latency data processing for time-critical edge operations
 */

#include <iostream>
#include <vector>
#include <string>
#include <thread>
#include <chrono>
#include <atomic>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <memory>
#include <fstream>
#include <json/json.h>
#include <opencv2/opencv.hpp>

// Forward declarations
class SensorData;
class ProcessingResult;
class EdgeProcessor;

/**
 * Sensor data structure
 */
struct SensorData {
    std::string sensor_id;
    std::string sensor_type;
    std::chrono::system_clock::time_point timestamp;
    std::vector<uint8_t> raw_data;
    std::map<std::string, std::string> metadata;
    
    SensorData(const std::string& id, const std::string& type) 
        : sensor_id(id), sensor_type(type), timestamp(std::chrono::system_clock::now()) {}
};

/**
 * Processing result structure
 */
struct ProcessingResult {
    std::string job_id;
    std::string processor_type;
    std::chrono::system_clock::time_point processed_at;
    std::map<std::string, double> metrics;
    std::vector<std::map<std::string, double>> detections;
    bool success;
    std::string error_message;
    
    ProcessingResult(const std::string& id, const std::string& type)
        : job_id(id), processor_type(type), processed_at(std::chrono::system_clock::now()), success(false) {}
};

/**
 * Base processor interface
 */
class BaseProcessor {
public:
    virtual ~BaseProcessor() = default;
    virtual ProcessingResult process(const SensorData& data) = 0;
    virtual bool initialize() = 0;
    virtual void shutdown() = 0;
    virtual std::string getType() const = 0;
};

/**
 * Traffic video processor using OpenCV
 */
class TrafficVideoProcessor : public BaseProcessor {
private:
    cv::HOGDescriptor hog_;
    cv::CascadeClassifier car_cascade_;
    bool initialized_;
    
public:
    TrafficVideoProcessor() : initialized_(false) {
        hog_.setSVMDetector(cv::HOGDescriptor::getDefaultPeopleDetector());
    }
    
    bool initialize() override {
        try {
            // Load cascade classifier for vehicle detection
            if (!car_cascade_.load("data/haarcascade_car.xml")) {
                std::cerr << "Warning: Could not load car cascade classifier" << std::endl;
            }
            
            initialized_ = true;
            std::cout << "Traffic video processor initialized" << std::endl;
            return true;
        } catch (const std::exception& e) {
            std::cerr << "Failed to initialize traffic processor: " << e.what() << std::endl;
            return false;
        }
    }
    
    ProcessingResult process(const SensorData& data) override {
        ProcessingResult result(data.sensor_id + "_" + std::to_string(
            std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count()), "traffic");
        
        if (!initialized_) {
            result.error_message = "Processor not initialized";
            return result;
        }
        
        try {
            // Convert raw data to OpenCV Mat
            cv::Mat frame = cv::imdecode(data.raw_data, cv::IMREAD_COLOR);
            if (frame.empty()) {
                result.error_message = "Failed to decode image data";
                return result;
            }
            
            // Detect vehicles
            std::vector<cv::Rect> vehicles;
            cv::Mat gray;
            cv::cvtColor(frame, gray, cv::COLOR_BGR2GRAY);
            
            if (!car_cascade_.empty()) {
                car_cascade_.detectMultiScale(gray, vehicles, 1.1, 3, 0, cv::Size(30, 30));
            }
            
            // Calculate traffic metrics
            double vehicle_count = static_cast<double>(vehicles.size());
            double frame_density = vehicle_count / (frame.rows * frame.cols / 10000.0); // vehicles per 100x100 area
            double congestion_level = std::min(frame_density / 5.0, 1.0); // normalize to 0-1
            
            // Store results
            result.metrics["vehicle_count"] = vehicle_count;
            result.metrics["congestion_level"] = congestion_level;
            result.metrics["frame_width"] = static_cast<double>(frame.cols);
            result.metrics["frame_height"] = static_cast<double>(frame.rows);
            result.metrics["processing_time_ms"] = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now() - result.processed_at).count();
            
            // Store detections
            for (const auto& vehicle : vehicles) {
                std::map<std::string, double> detection;
                detection["x"] = static_cast<double>(vehicle.x);
                detection["y"] = static_cast<double>(vehicle.y);
                detection["width"] = static_cast<double>(vehicle.width);
                detection["height"] = static_cast<double>(vehicle.height);
                detection["confidence"] = 0.8; // Mock confidence
                result.detections.push_back(detection);
            }
            
            result.success = true;
            
        } catch (const std::exception& e) {
            result.error_message = "Processing error: " + std::string(e.what());
        }
        
        return result;
    }
    
    void shutdown() override {
        initialized_ = false;
        std::cout << "Traffic video processor shutdown" << std::endl;
    }
    
    std::string getType() const override {
        return "traffic_video";
    }
};

/**
 * Audio anomaly detector for crime detection
 */
class AudioAnomalyProcessor : public BaseProcessor {
private:
    bool initialized_;
    double noise_threshold_;
    std::vector<double> baseline_spectrum_;
    
public:
    AudioAnomalyProcessor() : initialized_(false), noise_threshold_(0.5) {}
    
    bool initialize() override {
        try {
            // Initialize baseline spectrum (mock data)
            baseline_spectrum_.resize(1024);
            for (size_t i = 0; i < baseline_spectrum_.size(); ++i) {
                baseline_spectrum_[i] = 0.1 + 0.05 * sin(i * 0.01);
            }
            
            initialized_ = true;
            std::cout << "Audio anomaly processor initialized" << std::endl;
            return true;
        } catch (const std::exception& e) {
            std::cerr << "Failed to initialize audio processor: " << e.what() << std::endl;
            return false;
        }
    }
    
    ProcessingResult process(const SensorData& data) override {
        ProcessingResult result(data.sensor_id + "_" + std::to_string(
            std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count()), "audio_anomaly");
        
        if (!initialized_) {
            result.error_message = "Processor not initialized";
            return result;
        }
        
        try {
            // Convert raw audio data to samples (simplified)
            std::vector<double> samples;
            for (size_t i = 0; i < data.raw_data.size() - 1; i += 2) {
                int16_t sample = (data.raw_data[i + 1] << 8) | data.raw_data[i];
                samples.push_back(static_cast<double>(sample) / 32768.0);
            }
            
            if (samples.empty()) {
                result.error_message = "No audio samples found";
                return result;
            }
            
            // Calculate audio features
            double rms = 0.0;
            for (double sample : samples) {
                rms += sample * sample;
            }
            rms = sqrt(rms / samples.size());
            
            // Simple anomaly detection based on RMS level
            double anomaly_score = std::max(0.0, (rms - noise_threshold_) / noise_threshold_);
            bool is_anomaly = anomaly_score > 0.5;
            
            // Calculate frequency features (simplified FFT approximation)
            double high_freq_energy = 0.0;
            for (size_t i = samples.size() / 2; i < samples.size(); ++i) {
                high_freq_energy += samples[i] * samples[i];
            }
            high_freq_energy /= (samples.size() / 2);
            
            // Store results
            result.metrics["rms_level"] = rms;
            result.metrics["anomaly_score"] = anomaly_score;
            result.metrics["is_anomaly"] = is_anomaly ? 1.0 : 0.0;
            result.metrics["high_freq_energy"] = high_freq_energy;
            result.metrics["sample_count"] = static_cast<double>(samples.size());
            result.metrics["processing_time_ms"] = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now() - result.processed_at).count();
            
            if (is_anomaly) {
                std::map<std::string, double> detection;
                detection["type"] = 1.0; // 1 = audio anomaly
                detection["confidence"] = anomaly_score;
                detection["timestamp"] = std::chrono::duration_cast<std::chrono::seconds>(
                    result.processed_at.time_since_epoch()).count();
                result.detections.push_back(detection);
            }
            
            result.success = true;
            
        } catch (const std::exception& e) {
            result.error_message = "Processing error: " + std::string(e.what());
        }
        
        return result;
    }
    
    void shutdown() override {
        initialized_ = false;
        std::cout << "Audio anomaly processor shutdown" << std::endl;
    }
    
    std::string getType() const override {
        return "audio_anomaly";
    }
};

/**
 * Environmental data processor
 */
class EnvironmentDataProcessor : public BaseProcessor {
private:
    bool initialized_;
    std::map<std::string, double> historical_averages_;
    
public:
    EnvironmentDataProcessor() : initialized_(false) {}
    
    bool initialize() override {
        try {
            // Initialize historical averages
            historical_averages_["temperature"] = 20.0;
            historical_averages_["humidity"] = 50.0;
            historical_averages_["pm25"] = 15.0;
            historical_averages_["noise_level"] = 45.0;
            
            initialized_ = true;
            std::cout << "Environment data processor initialized" << std::endl;
            return true;
        } catch (const std::exception& e) {
            std::cerr << "Failed to initialize environment processor: " << e.what() << std::endl;
            return false;
        }
    }
    
    ProcessingResult process(const SensorData& data) override {
        ProcessingResult result(data.sensor_id + "_" + std::to_string(
            std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count()), "environment");
        
        if (!initialized_) {
            result.error_message = "Processor not initialized";
            return result;
        }
        
        try {
            // Parse environmental data (assume JSON format in metadata)
            Json::Value env_data;
            Json::Reader reader;
            
            // Mock environmental data parsing
            double temperature = 20.0 + (rand() % 20) - 10; // 10-30°C
            double humidity = 50.0 + (rand() % 40) - 20;    // 30-70%
            double pm25 = 15.0 + (rand() % 30);             // 15-45 µg/m³
            double noise_level = 45.0 + (rand() % 40);      // 45-85 dB
            
            // Calculate deviations from historical averages
            double temp_deviation = abs(temperature - historical_averages_["temperature"]) / historical_averages_["temperature"];
            double humidity_deviation = abs(humidity - historical_averages_["humidity"]) / historical_averages_["humidity"];
            double pm25_deviation = abs(pm25 - historical_averages_["pm25"]) / historical_averages_["pm25"];
            double noise_deviation = abs(noise_level - historical_averages_["noise_level"]) / historical_averages_["noise_level"];
            
            // Calculate overall environmental health score
            double health_score = 1.0 - (temp_deviation + humidity_deviation + pm25_deviation + noise_deviation) / 4.0;
            health_score = std::max(0.0, std::min(1.0, health_score));
            
            // Air quality index calculation (simplified)
            double aqi = pm25 * 2.0; // Rough approximation
            
            // Store results
            result.metrics["temperature"] = temperature;
            result.metrics["humidity"] = humidity;
            result.metrics["pm25"] = pm25;
            result.metrics["noise_level"] = noise_level;
            result.metrics["air_quality_index"] = aqi;
            result.metrics["health_score"] = health_score;
            result.metrics["temp_deviation"] = temp_deviation;
            result.metrics["processing_time_ms"] = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now() - result.processed_at).count();
            
            // Check for environmental alerts
            if (aqi > 100 || noise_level > 75 || temp_deviation > 0.3) {
                std::map<std::string, double> detection;
                detection["alert_type"] = (aqi > 100) ? 1.0 : (noise_level > 75) ? 2.0 : 3.0; // 1=air, 2=noise, 3=temp
                detection["severity"] = std::max({aqi / 200.0, noise_level / 100.0, temp_deviation});
                detection["timestamp"] = std::chrono::duration_cast<std::chrono::seconds>(
                    result.processed_at.time_since_epoch()).count();
                result.detections.push_back(detection);
            }
            
            result.success = true;
            
        } catch (const std::exception& e) {
            result.error_message = "Processing error: " + std::string(e.what());
        }
        
        return result;
    }
    
    void shutdown() override {
        initialized_ = false;
        std::cout << "Environment data processor shutdown" << std::endl;
    }
    
    std::string getType() const override {
        return "environment";
    }
};

/**
 * Main edge processor orchestrator
 */
class EdgeProcessor {
private:
    std::vector<std::unique_ptr<BaseProcessor>> processors_;
    std::queue<SensorData> input_queue_;
    std::queue<ProcessingResult> output_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_condition_;
    std::atomic<bool> running_;
    std::vector<std::thread> worker_threads_;
    size_t num_workers_;
    
public:
    EdgeProcessor(size_t num_workers = std::thread::hardware_concurrency()) 
        : running_(false), num_workers_(num_workers) {}
    
    ~EdgeProcessor() {
        shutdown();
    }
    
    bool initialize() {
        try {
            // Create processors
            processors_.push_back(std::make_unique<TrafficVideoProcessor>());
            processors_.push_back(std::make_unique<AudioAnomalyProcessor>());
            processors_.push_back(std::make_unique<EnvironmentDataProcessor>());
            
            // Initialize all processors
            for (auto& processor : processors_) {
                if (!processor->initialize()) {
                    std::cerr << "Failed to initialize processor: " << processor->getType() << std::endl;
                    return false;
                }
            }
            
            // Start worker threads
            running_ = true;
            for (size_t i = 0; i < num_workers_; ++i) {
                worker_threads_.emplace_back([this]() { this->workerLoop(); });
            }
            
            std::cout << "Edge processor initialized with " << num_workers_ << " workers" << std::endl;
            return true;
            
        } catch (const std::exception& e) {
            std::cerr << "Failed to initialize edge processor: " << e.what() << std::endl;
            return false;
        }
    }
    
    void addSensorData(const SensorData& data) {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        input_queue_.push(data);
        queue_condition_.notify_one();
    }
    
    bool getProcessingResult(ProcessingResult& result) {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        if (output_queue_.empty()) {
            return false;
        }
        
        result = output_queue_.front();
        output_queue_.pop();
        return true;
    }
    
    void workerLoop() {
        while (running_) {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            queue_condition_.wait(lock, [this]() { return !input_queue_.empty() || !running_; });
            
            if (!running_) break;
            
            if (input_queue_.empty()) continue;
            
            SensorData data = input_queue_.front();
            input_queue_.pop();
            lock.unlock();
            
            // Find appropriate processor
            BaseProcessor* processor = nullptr;
            for (auto& p : processors_) {
                if (p->getType().find(data.sensor_type) != std::string::npos ||
                    (data.sensor_type == "camera" && p->getType() == "traffic_video") ||
                    (data.sensor_type == "microphone" && p->getType() == "audio_anomaly") ||
                    (data.sensor_type == "environment" && p->getType() == "environment")) {
                    processor = p.get();
                    break;
                }
            }
            
            if (processor) {
                ProcessingResult result = processor->process(data);
                
                std::lock_guard<std::mutex> output_lock(queue_mutex_);
                output_queue_.push(result);
            }
        }
    }
    
    void shutdown() {
        running_ = false;
        queue_condition_.notify_all();
        
        for (auto& thread : worker_threads_) {
            if (thread.joinable()) {
                thread.join();
            }
        }
        
        for (auto& processor : processors_) {
            processor->shutdown();
        }
        
        worker_threads_.clear();
        processors_.clear();
        
        std::cout << "Edge processor shutdown complete" << std::endl;
    }
    
    void printStats() const {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        std::cout << "Edge Processor Stats:" << std::endl;
        std::cout << "  Input queue size: " << input_queue_.size() << std::endl;
        std::cout << "  Output queue size: " << output_queue_.size() << std::endl;
        std::cout << "  Active workers: " << worker_threads_.size() << std::endl;
        std::cout << "  Active processors: " << processors_.size() << std::endl;
    }
};

/**
 * Main function for standalone execution
 */
int main(int argc, char* argv[]) {
    std::cout << "High-Performance Edge Processor v1.0" << std::endl;
    std::cout << "=====================================" << std::endl;
    
    // Initialize processor
    EdgeProcessor processor(4); // 4 worker threads
    if (!processor.initialize()) {
        std::cerr << "Failed to initialize edge processor" << std::endl;
        return 1;
    }
    
    // Simulate sensor data processing
    std::cout << "Simulating sensor data processing..." << std::endl;
    
    for (int i = 0; i < 10; ++i) {
        // Create mock sensor data
        SensorData camera_data("camera_01", "camera");
        camera_data.raw_data.resize(1024 * 768 * 3); // Mock image data
        std::fill(camera_data.raw_data.begin(), camera_data.raw_data.end(), rand() % 256);
        
        SensorData audio_data("microphone_01", "microphone");
        audio_data.raw_data.resize(4096); // Mock audio data
        std::fill(audio_data.raw_data.begin(), audio_data.raw_data.end(), rand() % 256);
        
        SensorData env_data("sensor_01", "environment");
        env_data.raw_data.resize(64); // Mock environmental data
        
        // Add to processor
        processor.addSensorData(camera_data);
        processor.addSensorData(audio_data);
        processor.addSensorData(env_data);
        
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    
    // Wait for processing and collect results
    std::this_thread::sleep_for(std::chrono::seconds(2));
    
    ProcessingResult result;
    int results_count = 0;
    while (processor.getProcessingResult(result)) {
        std::cout << "Processing Result #" << ++results_count << ":" << std::endl;
        std::cout << "  Job ID: " << result.job_id << std::endl;
        std::cout << "  Type: " << result.processor_type << std::endl;
        std::cout << "  Success: " << (result.success ? "Yes" : "No") << std::endl;
        
        if (!result.success) {
            std::cout << "  Error: " << result.error_message << std::endl;
        } else {
            std::cout << "  Metrics:" << std::endl;
            for (const auto& metric : result.metrics) {
                std::cout << "    " << metric.first << ": " << metric.second << std::endl;
            }
            std::cout << "  Detections: " << result.detections.size() << std::endl;
        }
        std::cout << std::endl;
    }
    
    processor.printStats();
    
    std::cout << "Processing complete. Shutting down..." << std::endl;
    processor.shutdown();
    
    return 0;
}
