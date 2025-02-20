"use client";

import { SubmitButton } from "@/components";
import { MinusCircleIcon, PlusCircleIcon } from "@/components/Icons";
import { api } from "@/lib";
import {
  Badge,
  Button,
  DatePicker,
  Divider,
  Flex,
  Form,
  Input,
  Select,
  Skeleton,
  Space,
  Table,
  Typography,
} from "antd";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";
import advancedUTC from "dayjs/plugin/utc";
import { RUNDECK_JOB_STATUS_COLOR } from "@/static/config";

dayjs.extend(advancedFormat);
dayjs.extend(advancedUTC);

const { Title, Text } = Typography;
const { useForm } = Form;

const EmailListForm = ({ label, name }) => (
  <Form.List
    name={name}
    rules={[
      {
        validator: async (_, names) => {
          if (!names || names.length < 1) {
            return Promise.reject(new Error("At least 1 emails"));
          }
        },
      },
    ]}
  >
    {(fields, { add, remove }, { errors }) => (
      <div className="w-full">
        <Flex align="center" justify="space-between">
          <div>
            <Text strong>{label}</Text>
          </div>
          <div>
            <Button
              type="dashed"
              onClick={() => add()}
              icon={<PlusCircleIcon />}
            >
              Add new
            </Button>
          </div>
        </Flex>
        {fields.map(({ key, ...field }) => (
          <Flex key={key} vertical>
            <Space className="w-full mb-4">
              <Form.Item
                {...field}
                validateTrigger={["onChange", "onBlur"]}
                rules={[
                  {
                    required: true,
                    whitespace: true,
                    type: "email",
                    message: "This is not a valid email",
                  },
                ]}
                className="w-full"
              >
                <Input placeholder="Email" type="email" className="w-full" />
              </Form.Item>
              {fields.length > 0 ? (
                <a
                  role="button"
                  onClick={(e) => {
                    e.preventDefault();
                    remove(field.name);
                  }}
                >
                  <MinusCircleIcon />
                </a>
              ) : null}
            </Space>
          </Flex>
        ))}
        <Form.Item>
          <Form.ErrorList errors={errors} />
        </Form.Item>
      </div>
    )}
  </Form.List>
);

const SettingsPage = () => {
  const [settings, setSettings] = useState({
    on_success_emails: [null],
    on_failure_emails: [null],
    on_exceeded_emails: [null],
  });
  const [loading, setLoading] = useState(false);
  const [admins, setAdmins] = useState([]);
  const [projects, setProjects] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [execList, setExecList] = useState([]);
  const [fetching, setFetching] = useState(true);
  const [preload, setPreload] = useState(true);
  const [newSetup, setNewSetup] = useState(false);
  const [form] = useForm();
  const router = useRouter();

  const onFinish = async (payload) => {
    setLoading(true);
    try {
      const apiData = await api(
        "PUT",
        `/admin/setting/${settings.id}`,
        payload
      );
      setSettings(apiData);
      setLoading(false);
      router.refresh();
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const onFinishSetup = async (payload) => {
    setLoading(true);
    try {
      const apiData = await api("POST", "/admin/settings", payload);
      if (apiData?.id) {
        setNewSetup(false);
        setSettings(apiData);
      }
      setLoading(false);
      router.refresh();
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const onSelectProject = async (p) => {
    try {
      const _jobs = await api("GET", `/rundeck/project/${p}/jobs`);
      if (_jobs?.length) {
        setJobs(_jobs.map(({ name: label, id: value }) => ({ value, label })));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const onRunJob = async ({ year_month }) => {
    try {
      await api("POST", `/rundeck/job/${settings?.job_id}/execs`, {
        year_month: dayjs(year_month).format("YYYY-MM"),
      });

      setPreload(true);
      router.refresh();
    } catch (err) {
      console.error(err);
    }
  };

  const fetchData = useCallback(async () => {
    try {
      if (preload) {
        setPreload(false);
        const _projects = await api("GET", "/rundeck/projects");
        if (_projects?.length) {
          setProjects(
            _projects.map(({ label, name: value }) => ({ value, label }))
          );
        }
        const { contacts: _admins } = await api("GET", "/admin/contacts");
        setAdmins(_admins?.map((a) => ({ label: a, value: a })));

        const { results: _settings } = await api("GET", "/admin/settings");
        if (_settings?.length === 0) {
          setNewSetup(true);
        }
        setSettings(_settings[0]);
        const { data: _execList } = await api(
          "GET",
          `/rundeck/job/${_settings[0]?.job_id}/execs`
        );
        setExecList(_execList);
        setFetching(false);
      }
    } catch (err) {
      console.error(err);
      setPreload(false);
      setFetching(false);
    }
  }, [preload]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="w-full h-auto space-y-4 pt-6">
      <Title level={2}>Automation Settings</Title>
      <Skeleton loading={fetching} title paragraph>
        {newSetup ? (
          <div className="w-1/2 space-y-6">
            <Title level={3}>Rundeck Integration Setup</Title>
            <Form form={form} onFinish={onFinishSetup} layout="vertical">
              <Form.Item
                label="Project"
                name="project_name"
                rules={[
                  {
                    required: true,
                  },
                ]}
              >
                <Select
                  placeholder="Select Project"
                  onSelect={onSelectProject}
                  options={projects}
                />
              </Form.Item>
              <Form.Item
                label="Job"
                name="job_id"
                rules={[
                  {
                    required: true,
                  },
                ]}
              >
                <Select placeholder="Select Job" options={jobs} />
              </Form.Item>
              <SubmitButton form={form} loading={loading}>
                Submit
              </SubmitButton>
            </Form>
          </div>
        ) : (
          <div className="w-full h-auto flex flex-col lg:flex-row align-start justify-between gap-6">
            <div className="w-full lg:w-4/12 space-y-2">
              <Title level={3}>Email Notifications</Title>
              <Form
                form={form}
                initialValues={settings}
                onFinish={onFinish}
                layout="vertical"
              >
                <Form.Item
                  label={<Text strong>On Success (DH Admins)</Text>}
                  name="on_success_emails"
                  rules={[
                    {
                      validator: async (_, values) => {
                        if (!values || values.length < 1) {
                          return Promise.reject(new Error("At least 1 emails"));
                        }
                      },
                    },
                  ]}
                >
                  <Select options={admins} mode="multiple" />
                </Form.Item>
                <EmailListForm
                  label="On Failure (Technical Support)"
                  name="on_failure_emails"
                />
                <EmailListForm
                  label="On Job Exceeded"
                  name="on_exceeded_emails"
                />

                <div className="w-full text-right">
                  <SubmitButton size="large" form={form} loading={loading}>
                    Save
                  </SubmitButton>
                </div>
              </Form>
            </div>
            <div className="w-full lg:w-8/12 border-l border-l-grey-100 px-6 space-y-6">
              <Title level={3}>Manual Executions</Title>
              <Flex align="center" justify="space-between" className="w-full">
                <div>
                  {execList?.[0]?.date_started && (
                    <Text type="secondary">
                      Last executed:{" "}
                      {dayjs
                        .utc(execList[0].date_started)
                        .local()
                        .format("MMMM Do, YYYY - h:mm A")}
                    </Text>
                  )}
                </div>
                <div>
                  <Form onFinish={onRunJob} layout="inline">
                    <Form.Item
                      name="year_month"
                      label="Publication Date"
                      rules={[
                        {
                          required: true,
                        },
                      ]}
                    >
                      <DatePicker
                        format={{
                          format: "YYYY-MM",
                          type: "mask",
                        }}
                      />
                    </Form.Item>
                    <Button htmlType="submit" type="primary">
                      Run Job Now
                    </Button>
                  </Form>
                </div>
              </Flex>
              <Divider />
              <div className="w-full space-y-2 pt-4">
                <Flex align="center" justify="space-between">
                  <div>
                    <Title level={4}>Recent Executions</Title>
                  </div>
                  <Button
                    onClick={() => {
                      setPreload(true);
                      router.refresh();
                    }}
                  >
                    Refresh
                  </Button>
                </Flex>
                <Table
                  dataSource={execList}
                  rowKey="id"
                  columns={[
                    {
                      key: "id",
                      dataIndex: "id",
                      title: "#",
                    },
                    {
                      key: "year_month",
                      dataIndex: "year_month",
                      title: "PUBLICATION DATE",
                    },
                    {
                      key: "date_started",
                      dataIndex: "date_started",
                      title: "CREATED AT",
                      render: (value) =>
                        dayjs.utc(value).local().format("DD/MM/YYYY h:mm A"),
                    },
                    {
                      key: "date_ended",
                      dataIndex: "date_ended",
                      title: "FINISHED AT",
                      render: (value) =>
                        value
                          ? dayjs.utc(value).local().format("DD/MM/YYYY h:mm A")
                          : "-",
                    },
                    {
                      key: "status",
                      dataIndex: "status",
                      title: "STATUS",
                      render: (status, { permalink }) => (
                        <a target="_blank" href={permalink}>
                          <Badge
                            color={RUNDECK_JOB_STATUS_COLOR?.[status]}
                            text={status}
                          />
                        </a>
                      ),
                    },
                  ]}
                />
              </div>
            </div>
          </div>
        )}
      </Skeleton>
    </div>
  );
};

export default SettingsPage;
