const startButton = document.getElementById("start-run");
const deleteLastFileCheckbox = document.getElementById("delete-last-file");
const jobIdElement = document.getElementById("job-id");
const jobStatusElement = document.getElementById("job-status");
const jobResultElement = document.getElementById("job-result");
const newspaperMetaElement = document.getElementById("newspaper-meta");
const newspaperContentElement = document.getElementById("newspaper-content");

const TERMINAL_STATUSES = new Set(["succeeded", "failed"]);

async function fetchLatestNewspaper() {
  try {
    const response = await fetch("/api/newspaper/latest");
    if (!response.ok) {
      throw new Error("latest newspaper not available");
    }
    const payload = await response.json();
    newspaperMetaElement.textContent = `当前文件：${payload.path}`;
    newspaperContentElement.innerHTML = payload.html;
  } catch (_error) {
    newspaperMetaElement.textContent = "暂无已生成简报。";
    newspaperContentElement.innerHTML =
      '<p class="placeholder">尚未生成简报。点击左侧按钮开始执行。</p>';
  }
}

function renderJobStatus(job) {
  jobIdElement.textContent = job.job_id;
  jobStatusElement.textContent = job.status;

  if (job.error) {
    jobResultElement.textContent = job.error;
    return;
  }

  if (!job.result) {
    jobResultElement.textContent = "任务已提交，等待后端完成。";
    return;
  }

  const summaryCount = job.result.summary_count ?? 0;
  const outputPath = job.result.output_path ?? "未输出文件";
  jobResultElement.textContent = `生成 ${summaryCount} 篇摘要，输出到 ${outputPath}`;
}

async function pollJob(jobId) {
  while (true) {
    const response = await fetch(`/api/runs/${jobId}`);
    const job = await response.json();
    renderJobStatus(job);

    if (TERMINAL_STATUSES.has(job.status)) {
      startButton.disabled = false;
      if (job.status === "succeeded") {
        await fetchLatestNewspaper();
      }
      return;
    }

    await new Promise((resolve) => window.setTimeout(resolve, 1500));
  }
}

async function startRun() {
  startButton.disabled = true;
  jobStatusElement.textContent = "提交中";
  jobResultElement.textContent = "浏览器正在向后端发起运行请求。";

  try {
    const response = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        delete_last_file: deleteLastFileCheckbox.checked,
        config_path: null,
      }),
    });
    if (!response.ok) {
      throw new Error("failed to start run");
    }
    const job = await response.json();
    renderJobStatus(job);
    await pollJob(job.job_id);
  } catch (error) {
    startButton.disabled = false;
    jobStatusElement.textContent = "失败";
    jobResultElement.textContent = `启动失败：${error.message}`;
  }
}

startButton.addEventListener("click", () => {
  void startRun();
});

void fetchLatestNewspaper();
