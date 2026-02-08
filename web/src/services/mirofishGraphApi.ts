import api from './api';

export type GraphNode = {
  uuid: string;
  name?: string;
  labels?: string[];
  attributes?: Record<string, unknown>;
  summary?: string;
  created_at?: string;
};

export type GraphEdge = {
  uuid: string;
  source_node_uuid: string;
  target_node_uuid: string;
  source_name?: string;
  target_name?: string;
  name?: string;
  fact_type?: string;
  fact?: string;
  episodes?: string[];
  created_at?: string;
  valid_at?: string;
  invalid_at?: string;
  expired_at?: string;
};

export type GraphData = {
  nodes?: GraphNode[];
  edges?: GraphEdge[];
  node_count?: number;
  edge_count?: number;
};

export type GraphOntology = {
  entity_types?: Array<{ name: string }>;
  relation_types?: Array<{ name: string; source_type: string; target_type: string }>;
};

export type GraphProject = {
  project_id: string;
  name?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  files?: Array<{ filename?: string; size?: number }>;
  total_text_length?: number;
  ontology?: GraphOntology;
  analysis_summary?: string;
  graph_id?: string;
  graph_build_task_id?: string;
  simulation_requirement?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  error?: string;
};

export type GraphTask = {
  task_id: string;
  status: string;
  progress?: number;
  message?: string;
  result?: Record<string, unknown>;
  error?: string;
};

export type ApiResponse<T> = {
  success: boolean;
  data?: T;
  error?: string;
};

export const generateOntology = async (formData: FormData): Promise<ApiResponse<GraphProject>> => {
  return api.post('/mirofish/graph/ontology/generate', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 300000,
  });
};

export const buildGraph = async (
  projectId: string,
  graphName?: string
): Promise<ApiResponse<{ project_id?: string; task_id?: string; message?: string }>> => {
  return api.post(
    '/mirofish/graph/build',
    {
      project_id: projectId,
      graph_name: graphName,
    },
    { timeout: 300000 }
  );
};

export const getTaskStatus = async (taskId: string): Promise<ApiResponse<GraphTask>> => {
  return api.get(`/mirofish/graph/task/${taskId}`, { timeout: 300000 });
};

export const getGraphData = async (graphId: string): Promise<ApiResponse<GraphData>> => {
  return api.get(`/mirofish/graph/data/${graphId}`, { timeout: 300000 });
};

export const getProject = async (projectId: string): Promise<ApiResponse<GraphProject>> => {
  return api.get(`/mirofish/graph/project/${projectId}`, { timeout: 300000 });
};
