import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'

interface SparkConfig {
  driver_memory: string
  executor_memory: string
  executor_cores: number
  shuffle_partitions: number
  default_parallelism: number
  off_heap_enabled: boolean
  off_heap_size: string
  fetch_size: number
  num_partitions: number
}

const PRESET_CONFIGS = {
  small: {
    driver_memory: "4g",
    executor_memory: "4g",
    executor_cores: 2,
    shuffle_partitions: 50,
    default_parallelism: 50,
    off_heap_enabled: false,
    off_heap_size: "4g",
    fetch_size: 5000,
    num_partitions: 5
  },
  medium: {
    driver_memory: "10g",
    executor_memory: "10g",
    executor_cores: 4,
    shuffle_partitions: 200,
    default_parallelism: 200,
    off_heap_enabled: true,
    off_heap_size: "10g",
    fetch_size: 10000,
    num_partitions: 10
  },
  large: {
    driver_memory: "20g",
    executor_memory: "20g",
    executor_cores: 5,
    shuffle_partitions: 400,
    default_parallelism: 400,
    off_heap_enabled: true,
    off_heap_size: "20g",
    fetch_size: 20000,
    num_partitions: 20
  }
}

export function SparkConfig() {
  const navigate = useNavigate()
  const [config, setConfig] = useState<SparkConfig>(PRESET_CONFIGS.medium)

  const handlePresetChange = (preset: keyof typeof PRESET_CONFIGS) => {
    setConfig(PRESET_CONFIGS[preset])
  }

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    localStorage.setItem('sparkConfig', JSON.stringify(config))
    navigate('/query')
  }

  return (
    <div className="container">
      <div className="page-header">
        <h2>Spark Configuration</h2>
      </div>

      <form onSubmit={handleSubmit} className="form-container">
        <div className="form-header">
          <h3>Performance Settings</h3>
        </div>

        <div className="form-body">
          <div className="form-group">
            <label htmlFor="preset">Server Size Preset</label>
            <select
              id="preset"
              className="mb-4"
              onChange={(e) => handlePresetChange(e.target.value as keyof typeof PRESET_CONFIGS)}
              defaultValue="medium"
            >
              <option value="small">Small Server (32GB RAM, 8 cores)</option>
              <option value="medium">Medium Server (64GB RAM, 16 cores)</option>
              <option value="large">Large Server (128GB RAM, 32 cores)</option>
            </select>
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label>Driver Memory</label>
              <input type="text" value={config.driver_memory} disabled />
            </div>

            <div className="form-group">
              <label>Executor Memory</label>
              <input type="text" value={config.executor_memory} disabled />
            </div>

            <div className="form-group">
              <label>Executor Cores</label>
              <input type="number" value={config.executor_cores} disabled />
            </div>

            <div className="form-group">
              <label>Shuffle Partitions</label>
              <input type="number" value={config.shuffle_partitions} disabled />
            </div>

            <div className="form-group">
              <label>Default Parallelism</label>
              <input type="number" value={config.default_parallelism} disabled />
            </div>

            <div className="form-group">
              <label>Off-Heap Enabled</label>
              <input type="text" value={config.off_heap_enabled ? "Yes" : "No"} disabled />
            </div>

            <div className="form-group">
              <label>Off-Heap Size</label>
              <input type="text" value={config.off_heap_size} disabled />
            </div>

            <div className="form-group">
              <label>Fetch Size</label>
              <input type="number" value={config.fetch_size} disabled />
            </div>

            <div className="form-group">
              <label>Number of Partitions</label>
              <input type="number" value={config.num_partitions} disabled />
            </div>
          </div>
        </div>

        <div className="form-footer">
          <button
            type="button"
            className="secondary-btn"
            onClick={() => navigate('/')}
          >
            Back
          </button>
          <button type="submit" className="generate-btn">
            Next: Query & Export
          </button>
        </div>
      </form>
    </div>
  )
} 