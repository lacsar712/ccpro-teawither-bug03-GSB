from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import status_ops
from .models import Garden, Trough, WitherBatch


class StatusConsistencyTestCase(TestCase):
    """首页状态卡、整页筛选、HTMX 局部表必须同源同数。"""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            "tester", "tester@example.com", "pw"
        )
        cls.garden = Garden.objects.create(
            name="测试园", altitudeBand="700-900m"
        )
        # 2 装叶中、3 萎凋中、1 可下槽
        cls.loading = [
            cls._make_trough("L-01", Trough.STATUS_LOADING),
            cls._make_trough("L-02", Trough.STATUS_LOADING),
        ]
        cls.withering = [
            cls._make_trough("W-01", Trough.STATUS_WITHERING),
            cls._make_trough("W-02", Trough.STATUS_WITHERING),
            cls._make_trough("W-03", Trough.STATUS_WITHERING),
        ]
        cls.ready = [cls._make_trough("R-01", Trough.STATUS_WITHERING)]
        cls._make_batch(cls.ready[0], actual=Decimal("35.00"))
        cls.ready[0].status = Trough.STATUS_READY
        cls.ready[0].save()

    @classmethod
    def _make_trough(cls, code, status):
        return Trough.objects.create(
            garden=cls.garden,
            troughCode=code,
            cultivar="测试品种",
            loadKg=Decimal("100.00"),
            status=status,
        )

    @classmethod
    def _make_batch(cls, trough, actual):
        return WitherBatch.objects.create(
            trough=trough,
            startedAt=timezone.now(),
            targetMoisture=Decimal("38.00"),
            actualMoisture=actual,
            rollGrade="一级",
        )

    def setUp(self):
        self.client.force_login(self.user)

    # -- 字面量与统计函数 --

    def test_normalize_status_is_identity_for_canonical_keys(self):
        for key in status_ops.STATUS_KEYS:
            self.assertEqual(status_ops.normalize_status(key), key)
        self.assertIsNone(status_ops.normalize_status(None))
        self.assertIsNone(status_ops.normalize_status("bogus"))

    def test_status_counts_matches_db_and_sums_to_total(self):
        counts = status_ops.status_counts()
        for key in status_ops.STATUS_KEYS:
            self.assertEqual(
                counts[key], Trough.objects.filter(status=key).count()
            )
        self.assertEqual(sum(counts.values()), Trough.objects.count())

    # -- 三条路径互相对得上 --

    def test_home_cards_match_status_counts(self):
        response = self.client.get(reverse("home"))
        counts = status_ops.status_counts()
        self.assertEqual(response.context["loading_count"], counts["loading"])
        self.assertEqual(response.context["withering_count"], counts["withering"])
        self.assertEqual(response.context["ready_count"], counts["ready"])

    def test_full_page_filter_returns_exact_status_rows(self):
        for key in status_ops.STATUS_KEYS:
            response = self.client.get(reverse("trough_list"), {"status": key})
            got = {t.pk for t in response.context["troughs"]}
            want = set(
                Trough.objects.filter(status=key).values_list("pk", flat=True)
            )
            self.assertEqual(got, want, f"整页筛选 status={key} 行集不对")

    def test_htmx_filter_matches_full_page_filter(self):
        for key in status_ops.STATUS_KEYS:
            full = self.client.get(reverse("trough_list"), {"status": key})
            partial = self.client.get(
                reverse("trough_list"),
                {"status": key},
                HTTP_HX_REQUEST="true",
            )
            want_rows = Trough.objects.filter(status=key).count()
            # 每行渲染一个状态 badge，整页与局部表行数都必须等于库中该状态数
            self.assertEqual(
                full.content.count(b'class="badge badge-'), want_rows
            )
            self.assertEqual(
                partial.content.count(b'class="badge badge-'), want_rows
            )
            for t in Trough.objects.filter(status=key):
                self.assertIn(t.troughCode.encode(), partial.content)

    def test_home_card_counts_equal_filtered_list_row_counts(self):
        home = self.client.get(reverse("home"))
        pairs = [
            ("loading_count", "loading"),
            ("withering_count", "withering"),
            ("ready_count", "ready"),
        ]
        for context_key, status in pairs:
            filtered = self.client.get(
                reverse("trough_list"), {"status": status}
            )
            rows = filtered.content.count(b'class="badge badge-')
            self.assertEqual(
                home.context[context_key],
                rows,
                f"首页 {context_key} 与列表 status={status} 行数不一致",
            )

    def test_status_change_moves_home_counts(self):
        trough = self.withering[0]
        self._make_batch(trough, actual=Decimal("36.00"))
        before = status_ops.status_counts()
        trough.status = Trough.STATUS_READY
        trough.save()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["ready_count"], before["ready"] + 1)
        self.assertEqual(
            response.context["withering_count"], before["withering"] - 1
        )
