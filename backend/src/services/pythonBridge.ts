import axios, { AxiosInstance } from "axios";

interface TriggerWorkflowRequest {
  student_id: string;
  session_id: string;
  trigger_type:
    | "session_end"
    | "quiz_completed"
    | "cognitive_threshold_breach"
    | "manual";
}

interface CognitiveLoadRequest {
  student_id: string;
  session_id: string;
}

interface InterventionRequest {
  student_id: string;
  reason: string;
  context: any;
}

interface WorkflowStatusResponse {
  workflow_id: string;
  status: string;
  student_id: string;
  session_id: string;
  agents_executed: string[];
  current_agent?: string;
  agent_outputs: any;
  errors: string[];
  started_at: number;
  completed_at?: number;
}

class PythonBridgeClient {
  private client: AxiosInstance;
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
    this.client = axios.create({
      baseURL: this.baseUrl,
      timeout: parseInt(process.env.AGENT_EXECUTION_TIMEOUT || "300000"),
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  /**
   * Trigger agent workflow execution
   */
  async triggerAgentWorkflow(
    studentId: string,
    sessionId: string,
    triggerType: TriggerWorkflowRequest["trigger_type"]
  ): Promise<{ workflow_id: string; status: string; message: string }> {
    try {
      const response = await this.client.post("/api/agents/trigger-workflow", {
        student_id: studentId,
        session_id: sessionId,
        trigger_type: triggerType,
      });

      console.log(
        `✅ Triggered ${triggerType} workflow for student ${studentId}: ${response.data.workflow_id}`
      );

      return response.data;
    } catch (error: any) {
      console.error("Error triggering agent workflow:", error.message);
      throw error;
    }
  }

  /**
   * Calculate cognitive load for a student session
   */
  async calculateCognitiveLoad(
    studentId: string,
    sessionId: string
  ): Promise<{
    cognitive_load_score: number;
    mental_fatigue_level: string;
    timestamp: number;
  }> {
    try {
      const response = await this.client.post(
        "/api/agents/calculate-cognitive-load",
        {
          student_id: studentId,
          session_id: sessionId,
        }
      );

      console.log(
        `📊 Cognitive load for student ${studentId}: ${response.data.cognitive_load_score} (${response.data.mental_fatigue_level})`
      );

      return response.data;
    } catch (error: any) {
      console.error("Error calculating cognitive load:", error.message);
      throw error;
    }
  }

  /**
   * Request immediate intervention for a student
   */
  async requestIntervention(
    studentId: string,
    reason: string,
    context: any = {}
  ): Promise<any> {
    try {
      const response = await this.client.post(
        "/api/agents/request-intervention",
        {
          student_id: studentId,
          reason,
          context,
        }
      );

      console.log(
        `🚨 Intervention requested for student ${studentId}: ${reason}`
      );

      return response.data;
    } catch (error: any) {
      console.error("Error requesting intervention:", error.message);
      throw error;
    }
  }

  /**
   * Get workflow execution status
   */
  async getWorkflowStatus(workflowId: string): Promise<WorkflowStatusResponse> {
    try {
      const response = await this.client.get(
        `/api/agents/workflow-status/${workflowId}`
      );

      return response.data;
    } catch (error: any) {
      console.error("Error getting workflow status:", error.message);
      throw error;
    }
  }

  /**
   * Request curriculum adjustment
   */
  async requestCurriculumAdjustment(
    studentId: string,
    learningPathId: string,
    reason: string,
    context: any = {}
  ): Promise<any> {
    try {
      const response = await this.client.post(
        "/api/agents/curriculum-adjustment",
        {
          student_id: studentId,
          learning_path_id: learningPathId,
          reason,
          context,
        }
      );

      console.log(
        `📚 Curriculum adjustment for student ${studentId}, path ${learningPathId}`
      );

      return response.data;
    } catch (error: any) {
      console.error("Error requesting curriculum adjustment:", error.message);
      throw error;
    }
  }

  /**
   * Health check for Python backend
   */
  async healthCheck(): Promise<{
    status: string;
    timestamp: string;
    services: any;
  }> {
    try {
      const response = await this.client.get("/health");
      return response.data;
    } catch (error: any) {
      console.error("Python backend health check failed:", error.message);
      throw error;
    }
  }
}

// Export singleton instance
export const pythonBridge = new PythonBridgeClient();
