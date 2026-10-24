#!/usr/bin/env python3
"""
Pruebas automatizadas unitarias para el CLI gh-pr-review.
Ref: Issue #127 (tipado de variables, falso positivo en resolve y truncado silencioso).
"""

import argparse
import importlib.util
import io
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

SCRIPT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "skills",
        "issue-driven-workflow",
        "bin",
        "gh-pr-review",
    )
)

from importlib.machinery import SourceFileLoader

loader = SourceFileLoader("gh_pr_review", SCRIPT_PATH)
spec = importlib.util.spec_from_loader("gh_pr_review", loader)
gh_pr_review = importlib.util.module_from_spec(spec)
loader.exec_module(gh_pr_review)


class TestGhPrReviewVariablesAndTyping(unittest.TestCase):
    """Verifica el tipado determinista de variables (-f vs -F) y eliminación de magic type conversion."""

    @patch("subprocess.run")
    def test_run_gh_graphql_variable_typing(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps({"data": {"test": True}})
        mock_run.return_value = mock_proc

        variables = {
            "str_num": "123",
            "str_at": "@archivo.txt",
            "str_bool": "true",
            "str_null": "null",
            "int_val": 42,
            "bool_val": True,
            "none_val": None,
        }

        res = gh_pr_review.run_gh_graphql("query { test }", variables)
        self.assertEqual(res, {"data": {"test": True}})

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]

        # int_val debe pasarse con -F (typed field)
        self.assertIn("-F", cmd)
        self.assertIn("int_val=42", cmd)
        idx_int = cmd.index("int_val=42")
        self.assertEqual(cmd[idx_int - 1], "-F")

        # Strings (incluso "123", "@archivo.txt", "true") deben pasarse con -f (raw string)
        for expected in ["str_num=123", "str_at=@archivo.txt", "str_bool=true", "str_null=null"]:
            self.assertIn(expected, cmd)
            idx = cmd.index(expected)
            self.assertEqual(cmd[idx - 1], "-f", f"{expected} debe usar -f")

        # bool_val (bool) no debe usar -F para evitar magic conversions
        idx_bool = cmd.index("bool_val=True")
        self.assertEqual(cmd[idx_bool - 1], "-f")

        # none_val debe omitirse
        self.assertFalse(any("none_val" in arg for arg in cmd))

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_cmd_reply_literal_body(self, mock_graphql):
        mock_graphql.return_value = {
            "data": {
                "addPullRequestReviewThreadReply": {
                    "comment": {
                        "id": "PRRC_1",
                        "databaseId": 1234,
                        "body": "123",
                        "createdAt": "2026-10-23T00:00:00Z",
                    }
                }
            }
        }

        args = argparse.Namespace(
            thread_id="PRRT_1",
            body="123",
            body_file=None,
        )
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            ret = gh_pr_review.cmd_reply(args)
            self.assertEqual(ret, 0)
            data = json.loads(mock_stdout.getvalue())
            self.assertTrue(data["success"])

        # Verificar variables enviadas a run_gh_graphql
        mock_graphql.assert_called_once()
        sent_vars = mock_graphql.call_args[0][1]
        self.assertEqual(sent_vars["body"], "123")
        self.assertIsInstance(sent_vars["body"], str)

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_cmd_reply_at_sign_body(self, mock_graphql):
        mock_graphql.return_value = {
            "data": {
                "addPullRequestReviewThreadReply": {
                    "comment": {
                        "id": "PRRC_2",
                        "databaseId": 1235,
                        "body": "@archivo.txt",
                        "createdAt": "2026-10-23T00:00:00Z",
                    }
                }
            }
        }

        args = argparse.Namespace(
            thread_id="PRRT_2",
            body="@archivo.txt",
            body_file=None,
        )
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            ret = gh_pr_review.cmd_reply(args)
            self.assertEqual(ret, 0)

        sent_vars = mock_graphql.call_args[0][1]
        self.assertEqual(sent_vars["body"], "@archivo.txt")


class TestGhPrReviewResolve(unittest.TestCase):
    """Verifica la validación estricta de isResolved y prevención de falsos positivos."""

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_resolve_single_thread_success(self, mock_graphql):
        mock_graphql.return_value = {
            "data": {
                "resolveReviewThread": {
                    "thread": {
                        "id": "PRRT_1",
                        "isResolved": True,
                    }
                }
            }
        }
        success, err = gh_pr_review.resolve_single_thread("PRRT_1")
        self.assertTrue(success)
        self.assertIsNone(err)

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_resolve_single_thread_false_positive_prevention(self, mock_graphql):
        # Caso 1: isResolved is False
        mock_graphql.return_value = {
            "data": {
                "resolveReviewThread": {
                    "thread": {
                        "id": "PRRT_1",
                        "isResolved": False,
                    }
                }
            }
        }
        success, err = gh_pr_review.resolve_single_thread("PRRT_1")
        self.assertFalse(success)
        self.assertIn("no confirmó el estado resuelto", err)

        # Caso 2: payload vacío / thread is None
        mock_graphql.return_value = {
            "data": {
                "resolveReviewThread": {
                    "thread": None
                }
            }
        }
        success, err = gh_pr_review.resolve_single_thread("PRRT_1")
        self.assertFalse(success)

        # Caso 3: resolveReviewThread is None
        mock_graphql.return_value = {
            "data": {
                "resolveReviewThread": None
            }
        }
        success, err = gh_pr_review.resolve_single_thread("PRRT_1")
        self.assertFalse(success)

        # Caso 4: data is None
        mock_graphql.return_value = {"data": None}
        success, err = gh_pr_review.resolve_single_thread("PRRT_1")
        self.assertFalse(success)

    @patch.object(gh_pr_review, "resolve_threads_batch")
    def test_cmd_resolve_reports_failure(self, mock_resolve_batch):
        mock_resolve_batch.return_value = ([], [{"threadId": "PRRT_FAIL", "error": "La mutación no confirmó el estado resuelto"}])

        args = argparse.Namespace(
            thread_ids=["PRRT_FAIL"],
            all=None,
            repo=None,
        )
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            ret = gh_pr_review.cmd_resolve(args)
            self.assertEqual(ret, 1)
            data = json.loads(mock_stdout.getvalue())
            self.assertFalse(data["success"])
            self.assertEqual(len(data["errors"]), 1)
            self.assertEqual(data["errors"][0]["threadId"], "PRRT_FAIL")


class TestGhPrReviewPaginationAndTruncation(unittest.TestCase):
    """Verifica paginación por cursor en hilos y señalización explícita de truncado."""

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_fetch_unresolved_threads_pagination(self, mock_graphql):
        # Página 1 (hasNextPage=True)
        page1 = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "pageInfo": {
                                "hasNextPage": True,
                                "endCursor": "cursor_p1",
                            },
                            "nodes": [
                                {"id": "THREAD_1", "isResolved": False},
                                {"id": "THREAD_2", "isResolved": True},
                            ],
                        }
                    }
                }
            }
        }
        # Página 2 (hasNextPage=False)
        page2 = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": "cursor_p2",
                            },
                            "nodes": [
                                {"id": "THREAD_3", "isResolved": False},
                            ],
                        }
                    }
                }
            }
        }
        mock_graphql.side_effect = [page1, page2]

        threads, err = gh_pr_review.fetch_unresolved_threads(100)
        self.assertIsNone(err)
        self.assertEqual(threads, ["THREAD_1", "THREAD_3"])
        self.assertEqual(mock_graphql.call_count, 2)

        # Comprobar cursor en segunda llamada
        first_call_vars = mock_graphql.call_args_list[0][0][1]
        second_call_vars = mock_graphql.call_args_list[1][0][1]
        self.assertNotIn("cursor", first_call_vars)
        self.assertEqual(second_call_vars.get("cursor"), "cursor_p1")

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_cmd_comments_pagination_and_truncation_detection(self, mock_graphql):
        # Página 1 con hilo con comentarios truncados (hasNextPage=True)
        page1 = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "title": "PR Grande",
                        "url": "https://github.com/example/pr/100",
                        "reviewThreads": {
                            "pageInfo": {
                                "hasNextPage": True,
                                "endCursor": "cur_page1",
                            },
                            "nodes": [
                                {
                                    "id": "T1",
                                    "isResolved": False,
                                    "path": "file1.py",
                                    "line": 10,
                                    "originalLine": 10,
                                    "diffSide": "RIGHT",
                                    "comments": {
                                        "pageInfo": {"hasNextPage": True, "endCursor": "cur_c1"},
                                        "nodes": [
                                            {
                                                "id": "C1",
                                                "databaseId": 1,
                                                "body": "Muchos comentarios",
                                                "author": {"login": "user1"},
                                                "createdAt": "2026-10-23T00:00:00Z",
                                                "url": "https://...",
                                            }
                                        ],
                                    },
                                }
                            ],
                        },
                    }
                }
            }
        }
        # Página 2 con hilo normal (hasNextPage=False)
        page2 = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "title": "PR Grande",
                        "url": "https://github.com/example/pr/100",
                        "reviewThreads": {
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": "cur_page2",
                            },
                            "nodes": [
                                {
                                    "id": "T2",
                                    "isResolved": False,
                                    "path": "file2.py",
                                    "line": 20,
                                    "originalLine": 20,
                                    "diffSide": "RIGHT",
                                    "comments": {
                                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                                        "nodes": [
                                            {
                                                "id": "C2",
                                                "databaseId": 2,
                                                "body": "Comentario único",
                                                "author": {"login": "user2"},
                                                "createdAt": "2026-10-23T00:00:00Z",
                                                "url": "https://...",
                                            }
                                        ],
                                    },
                                }
                            ],
                        },
                    }
                }
            }
        }
        mock_graphql.side_effect = [page1, page2]

        args = argparse.Namespace(
            pr=100,
            repo="owner/repo",
            all=False,
            detailed=False,
        )

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            ret = gh_pr_review.cmd_comments(args)
            self.assertEqual(ret, 0)
            data = json.loads(mock_stdout.getvalue())

            # Verificaciones de resumen
            self.assertEqual(data["prNumber"], 100)
            self.assertEqual(data["totalThreads"], 2)
            self.assertEqual(data["unresolvedCount"], 2)
            self.assertEqual(data["returnedThreads"], 2)
            # Truncado detectado debido a T1 (comments hasNextPage=True)
            self.assertTrue(data["truncated"])

            # Verificaciones por hilo
            t1 = data["threads"][0]
            self.assertEqual(t1["threadId"], "T1")
            self.assertTrue(t1["commentsTruncated"])

            t2 = data["threads"][1]
            self.assertEqual(t2["threadId"], "T2")
            self.assertFalse(t2["commentsTruncated"])


class TestGhPrReviewBatchResolve(unittest.TestCase):
    """Verifica resolución por lotes con alias GraphQL, particionamiento y tolerancia a fallos parciales."""

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_resolve_threads_batch_success(self, mock_graphql):
        mock_graphql.return_value = {
            "data": {
                "t0": {"thread": {"id": "THREAD_1", "isResolved": True}},
                "t1": {"thread": {"id": "THREAD_2", "isResolved": True}},
                "t2": {"thread": {"id": "THREAD_3", "isResolved": True}},
            }
        }
        resolved, errors = gh_pr_review.resolve_threads_batch(["THREAD_1", "THREAD_2", "THREAD_3"])
        self.assertEqual(resolved, ["THREAD_1", "THREAD_2", "THREAD_3"])
        self.assertEqual(errors, [])
        mock_graphql.assert_called_once()
        query, variables = mock_graphql.call_args[0]
        self.assertIn("$t0: ID!, $t1: ID!, $t2: ID!", query)
        self.assertIn("t0: resolveReviewThread(input: {threadId: $t0})", query)
        self.assertIn("t1: resolveReviewThread(input: {threadId: $t1})", query)
        self.assertIn("t2: resolveReviewThread(input: {threadId: $t2})", query)
        self.assertEqual(variables, {"t0": "THREAD_1", "t1": "THREAD_2", "t2": "THREAD_3"})

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_resolve_threads_batch_partial_failure(self, mock_graphql):
        # Simula respuesta con data para t0 y raw_errors para t1
        mock_graphql.return_value = {
            "data": {
                "t0": {"thread": {"id": "THREAD_OK", "isResolved": True}},
                "t1": None,
            },
            "error": "GraphQL Error: Could not resolve to a node with the global id of 'THREAD_BAD'",
            "raw_errors": [
                {
                    "path": ["t1"],
                    "message": "Could not resolve to a node with the global id of 'THREAD_BAD'",
                }
            ],
        }
        resolved, errors = gh_pr_review.resolve_threads_batch(["THREAD_OK", "THREAD_BAD"])
        self.assertEqual(resolved, ["THREAD_OK"])
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["threadId"], "THREAD_BAD")
        self.assertIn("Could not resolve to a node", errors[0]["error"])

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_resolve_threads_batch_unconfirmed_state(self, mock_graphql):
        mock_graphql.return_value = {
            "data": {
                "t0": {"thread": {"id": "THREAD_1", "isResolved": False}},
            }
        }
        resolved, errors = gh_pr_review.resolve_threads_batch(["THREAD_1"])
        self.assertEqual(resolved, [])
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["threadId"], "THREAD_1")
        self.assertIn("no confirmó el estado resuelto", errors[0]["error"])

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_resolve_threads_batch_total_failure(self, mock_graphql):
        mock_graphql.return_value = {
            "error": "Network timeout or rate limit exceeded",
        }
        resolved, errors = gh_pr_review.resolve_threads_batch(["T1", "T2"])
        self.assertEqual(resolved, [])
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]["threadId"], "T1")
        self.assertIn("Network timeout", errors[0]["error"])
        self.assertEqual(errors[1]["threadId"], "T2")
        self.assertIn("Network timeout", errors[1]["error"])

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_resolve_threads_batch_chunking(self, mock_graphql):
        # 55 hilos deben generar 2 mutaciones (lote 1 de 50, lote 2 de 5)
        threads = [f"THREAD_{i}" for i in range(55)]
        chunk1_data = {f"t{i}": {"thread": {"id": f"THREAD_{i}", "isResolved": True}} for i in range(50)}
        chunk2_data = {f"t{i}": {"thread": {"id": f"THREAD_{50+i}", "isResolved": True}} for i in range(5)}
        mock_graphql.side_effect = [{"data": chunk1_data}, {"data": chunk2_data}]

        resolved, errors = gh_pr_review.resolve_threads_batch(threads)
        self.assertEqual(len(resolved), 55)
        self.assertEqual(errors, [])
        self.assertEqual(mock_graphql.call_count, 2)

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_cmd_resolve_batch_integration(self, mock_graphql):
        mock_graphql.return_value = {
            "data": {
                "t0": {"thread": {"id": "T0", "isResolved": True}},
                "t1": {"thread": {"id": "T1", "isResolved": True}},
            }
        }
        args = argparse.Namespace(
            thread_ids=["T0", "T1"],
            all=None,
            repo=None,
        )
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            ret = gh_pr_review.cmd_resolve(args)
            self.assertEqual(ret, 0)
            data = json.loads(mock_stdout.getvalue())
            self.assertTrue(data["success"])
            self.assertEqual(data["resolvedCount"], 2)
            self.assertEqual(data["resolvedThreads"], ["T0", "T1"])
            self.assertEqual(data["errors"], [])


class TestGhPrReviewFiltering(unittest.TestCase):
    """Verifica el filtrado de hilos por estado y vigencia (--exclude-outdated)."""

    def _sample_threads_data(self):
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "title": "PR con hilos obsoletos",
                        "url": "https://github.com/example/pr/100",
                        "reviewThreads": {
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                            "nodes": [
                                {
                                    "id": "T1_ACTIVE",
                                    "isResolved": False,
                                    "isOutdated": False,
                                    "path": "file1.py",
                                    "line": 10,
                                    "originalLine": 10,
                                    "diffSide": "RIGHT",
                                    "comments": {
                                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                                        "nodes": [
                                            {
                                                "id": "C1",
                                                "databaseId": 1,
                                                "body": "Comentario activo",
                                                "author": {"login": "reviewer"},
                                                "createdAt": "2026-10-25T00:00:00Z",
                                                "url": "https://example.com/comment/1",
                                            }
                                        ],
                                    },
                                },
                                {
                                    "id": "T2_OUTDATED",
                                    "isResolved": False,
                                    "isOutdated": True,
                                    "path": "file2.py",
                                    "line": 20,
                                    "originalLine": 20,
                                    "diffSide": "RIGHT",
                                    "comments": {
                                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                                        "nodes": [
                                            {
                                                "id": "C2",
                                                "databaseId": 2,
                                                "body": "Comentario obsoleto",
                                                "author": {"login": "reviewer"},
                                                "createdAt": "2026-10-25T00:00:00Z",
                                                "url": "https://example.com/comment/2",
                                            }
                                        ],
                                    },
                                },
                                {
                                    "id": "T3_RESOLVED_OUTDATED",
                                    "isResolved": True,
                                    "isOutdated": True,
                                    "path": "file3.py",
                                    "line": 30,
                                    "originalLine": 30,
                                    "diffSide": "RIGHT",
                                    "comments": {
                                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                                        "nodes": [
                                            {
                                                "id": "C3",
                                                "databaseId": 3,
                                                "body": "Resuelto y obsoleto",
                                                "author": {"login": "reviewer"},
                                                "createdAt": "2026-10-25T00:00:00Z",
                                                "url": "https://example.com/comment/3",
                                            }
                                        ],
                                    },
                                },
                            ],
                        },
                    }
                }
            }
        }

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_cmd_comments_default_includes_outdated(self, mock_graphql):
        mock_graphql.return_value = self._sample_threads_data()
        args = argparse.Namespace(
            pr=100,
            repo="owner/repo",
            all=False,
            exclude_outdated=False,
            detailed=False,
        )

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            ret = gh_pr_review.cmd_comments(args)
            self.assertEqual(ret, 0)
            data = json.loads(mock_stdout.getvalue())

            # Por defecto, incluye no resueltos (activos y obsoletos)
            self.assertEqual(data["totalThreads"], 3)
            self.assertEqual(data["unresolvedCount"], 2)
            self.assertEqual(data["returnedThreads"], 2)
            returned_ids = [t["threadId"] for t in data["threads"]]
            self.assertEqual(returned_ids, ["T1_ACTIVE", "T2_OUTDATED"])

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_cmd_comments_exclude_outdated_filters_threads(self, mock_graphql):
        mock_graphql.return_value = self._sample_threads_data()
        args = argparse.Namespace(
            pr=100,
            repo="owner/repo",
            all=False,
            exclude_outdated=True,
            detailed=False,
        )

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            ret = gh_pr_review.cmd_comments(args)
            self.assertEqual(ret, 0)
            data = json.loads(mock_stdout.getvalue())

            # Con --exclude-outdated, se descarta T2_OUTDATED
            self.assertEqual(data["totalThreads"], 3)
            self.assertEqual(data["unresolvedCount"], 2)
            self.assertEqual(data["returnedThreads"], 1)
            returned_ids = [t["threadId"] for t in data["threads"]]
            self.assertEqual(returned_ids, ["T1_ACTIVE"])
            self.assertFalse(data["threads"][0]["isOutdated"])

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_cmd_comments_exclude_outdated_with_all_flag(self, mock_graphql):
        mock_graphql.return_value = self._sample_threads_data()
        args = argparse.Namespace(
            pr=100,
            repo="owner/repo",
            all=True,
            exclude_outdated=True,
            detailed=False,
        )

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            ret = gh_pr_review.cmd_comments(args)
            self.assertEqual(ret, 0)
            data = json.loads(mock_stdout.getvalue())

            # --all incluiría los 3, pero --exclude-outdated descarta T2 y T3
            self.assertEqual(data["totalThreads"], 3)
            self.assertEqual(data["returnedThreads"], 1)
            returned_ids = [t["threadId"] for t in data["threads"]]
            self.assertEqual(returned_ids, ["T1_ACTIVE"])

    def test_argparse_exclude_outdated(self):
        with patch("sys.argv", ["gh-pr-review", "comments", "100", "--exclude-outdated"]):
            with patch.object(gh_pr_review, "cmd_comments") as mock_cmd:
                mock_cmd.return_value = 0
                ret = gh_pr_review.main()
                self.assertEqual(ret, 0)
                mock_cmd.assert_called_once()
                parsed_args = mock_cmd.call_args[0][0]
                self.assertTrue(parsed_args.exclude_outdated)
                self.assertEqual(parsed_args.pr, 100)


class TestGhPrReviewContextAndComments(unittest.TestCase):
    """Verifica la ingesta extendida de reviews, comentarios y veredicto con soporte para --threads-only."""

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_cmd_comments_extended_context(self, mock_graphql):
        mock_graphql.return_value = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "title": "PR Con Contexto",
                        "url": "https://github.com/example/pr/101",
                        "reviewDecision": "CHANGES_REQUESTED",
                        "reviews": {
                            "nodes": [
                                {
                                    "author": {"login": "lead_reviewer"},
                                    "state": "CHANGES_REQUESTED",
                                    "body": "Por favor corregir el manejo de errores.",
                                    "submittedAt": "2026-10-24T10:00:00Z",
                                }
                            ]
                        },
                        "comments": {
                            "nodes": [
                                {
                                    "author": {"login": "general_commenter"},
                                    "body": "Excelente iniciativa.",
                                    "createdAt": "2026-10-24T09:30:00Z",
                                }
                            ]
                        },
                        "reviewThreads": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {
                                    "id": "T1",
                                    "isResolved": False,
                                    "path": "app.py",
                                    "line": 42,
                                    "originalLine": 40,
                                    "diffSide": "RIGHT",
                                    "comments": {
                                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                                        "nodes": [
                                            {
                                                "id": "C1",
                                                "databaseId": 101,
                                                "body": "Ajustar aquí",
                                                "author": {"login": "lead_reviewer"},
                                                "createdAt": "2026-10-24T10:05:00Z",
                                                "url": "https://...",
                                            }
                                        ],
                                    },
                                }
                            ],
                        },
                    }
                }
            }
        }

        args = argparse.Namespace(
            pr=101,
            repo="owner/repo",
            all=False,
            detailed=False,
            threads_only=False,
        )

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            ret = gh_pr_review.cmd_comments(args)
            self.assertEqual(ret, 0)
            data = json.loads(mock_stdout.getvalue())

            self.assertEqual(data["prNumber"], 101)
            self.assertEqual(data["reviewDecision"], "CHANGES_REQUESTED")
            self.assertEqual(len(data["reviews"]), 1)
            self.assertEqual(data["reviews"][0]["author"], "lead_reviewer")
            self.assertEqual(data["reviews"][0]["state"], "CHANGES_REQUESTED")
            self.assertEqual(data["reviews"][0]["body"], "Por favor corregir el manejo de errores.")
            self.assertEqual(data["reviews"][0]["submittedAt"], "2026-10-24T10:00:00Z")

            self.assertEqual(len(data["prComments"]), 1)
            self.assertEqual(data["prComments"][0]["author"], "general_commenter")
            self.assertEqual(data["prComments"][0]["body"], "Excelente iniciativa.")

            self.assertEqual(len(data["threads"]), 1)
            self.assertEqual(data["threads"][0]["threadId"], "T1")

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_cmd_comments_threads_only(self, mock_graphql):
        mock_graphql.return_value = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "title": "PR Con Contexto",
                        "url": "https://github.com/example/pr/101",
                        "reviewDecision": "APPROVED",
                        "reviews": {
                            "nodes": [
                                {
                                    "author": {"login": "lead"},
                                    "state": "APPROVED",
                                    "body": "LGTM",
                                    "submittedAt": "2026-10-24T10:00:00Z",
                                }
                            ]
                        },
                        "comments": {"nodes": []},
                        "reviewThreads": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [],
                        },
                    }
                }
            }
        }

        args = argparse.Namespace(
            pr=101,
            repo="owner/repo",
            all=False,
            detailed=False,
            threads_only=True,
        )

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            ret = gh_pr_review.cmd_comments(args)
            self.assertEqual(ret, 0)
            data = json.loads(mock_stdout.getvalue())

            self.assertNotIn("reviewDecision", data)
            self.assertNotIn("reviews", data)
            self.assertNotIn("prComments", data)
            self.assertIn("threads", data)
            self.assertEqual(data["totalThreads"], 0)

    @patch.object(gh_pr_review, "run_gh_graphql")
    def test_cmd_comments_ghost_author(self, mock_graphql):
        mock_graphql.return_value = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "title": "PR Ghost",
                        "url": "https://github.com/example/pr/102",
                        "reviewDecision": None,
                        "reviews": {
                            "nodes": [
                                {
                                    "author": None,
                                    "state": "COMMENTED",
                                    "body": "Ghost review",
                                    "submittedAt": "2026-10-24T10:00:00Z",
                                }
                            ]
                        },
                        "comments": {
                            "nodes": [
                                {
                                    "author": None,
                                    "body": "Ghost comment",
                                    "createdAt": "2026-10-24T10:00:00Z",
                                }
                            ]
                        },
                        "reviewThreads": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [],
                        },
                    }
                }
            }
        }

        args = argparse.Namespace(
            pr=102,
            repo="owner/repo",
            all=False,
            detailed=False,
            threads_only=False,
        )

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            ret = gh_pr_review.cmd_comments(args)
            self.assertEqual(ret, 0)
            data = json.loads(mock_stdout.getvalue())

            self.assertEqual(data["reviews"][0]["author"], "unknown")
            self.assertEqual(data["prComments"][0]["author"], "unknown")


if __name__ == "__main__":
    unittest.main()
