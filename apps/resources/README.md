# Workings

## Understanding Django Mixin Execution & Flow

The Problem (AttributeError): When we attempt to access attributes initialized by parent mixins at the very start of dispatch() results in an AttributeError. For example: When writing a custom child mixin (e.g., ResourceOwnerOrgOwnerAdminRequired) that inherits from two other mixins OrgMembershipRequired and ResourceMembershipRequired. We cannot access self.resource and self.role in our child mixins because they are not yet been initialized by parent mixins.

The Root Cause (MRO & Cooperative Inheritance): Python handles multiple inheritance using the MRO (Method Resolution Order). When a class calls super().dispatch(), Python does not execute all parent methods simultaneously. Instead, it moves linearly, step-by-step down the inheritance chain from left parent to the right parent. Because parent dispatch() methods haven't executed yet when the child mixin starts, their variables do not exist yet.

Solution A (Top-Down Execution): Letting super().dispatch() run first allows the parent mixins to initialize their variables down the chain before the child mixin performs its validation checks.

Solution B (Lazy-Loading / Memoization - Recommended): Implementing helper methods (like self.get_resource() or self.get_role() guarded by hasattr) completely decouples attribute initialization from rigid execution order. When called from anywhere in the child mixin, they evaluate, cache, and return the required data safely on demand.

### To do

* While listing clasrooms and inside lst classrooms in student show hierarchy. Show a common function that takes a classroom ids and gives you json to map.
